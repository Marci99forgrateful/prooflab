import Mathlib.Data.Set.Basic
import Mathlib.Algebra.Group.Basic
import Mathlib.Algebra.Ring.Basic
import Mathlib.Tactic.Ring
import Aesop

/-!
Structured, persistent tactic sessions. Every branch restores a full Lean
elaboration snapshot. The Python layer never manufactures mathematical states.
This module provides no axiom, unsafe definition, or admitted proof.
-/
open Lean Meta Elab Tactic

namespace ProofLab

def jsonObj (xs : List (String × Json)) : Json := Json.mkObj xs
def str (s : String) : Json := toJson s

def describeExpr (e : Expr) : MetaM Json := do
  let e ← instantiateMVars e
  let reduced ← whnf e
  return jsonObj [
    ("text", str (← ppExpr e).pretty),
    ("head", str (reduced.getAppFn.constName?.getD Name.anonymous).toString),
    ("forall", toJson reduced.isForall)]

def snapshot : TacticM Json := do
  let mut out := #[]
  for g in ← getUnsolvedGoals do
    let desc ← g.withContext do
      let mut hyps := #[]
      for d in ← getLCtx do
        unless d.isImplementationDetail do
          hyps := hyps.push (jsonObj [
            ("name", str d.userName.toString),
            ("id", str d.fvarId.name.toString),
            ("is_proof", toJson (← isProp d.type)),
            ("type", ← describeExpr d.type)])
      pure <| jsonObj [
        ("id", str g.name.toString),
        ("target", ← describeExpr (← g.getType)),
        ("hypotheses", toJson hyps)]
    out := out.push desc
  return toJson out

def emit (stdout : IO.FS.Handle) (j : Json) : TacticM Unit := do
  stdout.putStrLn ("PROOFLAB:" ++ j.compress)
  stdout.flush

def fieldStr (j : Json) (k : String) : Except String String := do
  (← j.getObjVal? k).getStr?

def fieldNat (j : Json) (k : String) : Except String Nat := do
  (← j.getObjVal? k).getNat?

elab "prooflab_session" input:str output:str : tactic => do
  -- The Lean frontend isolates command stdin/stdout. Private POSIX FIFOs keep
  -- the structured protocol separate from captured elaborator diagnostics.
  let stdin ← IO.FS.Handle.mk input.getString .read
  let stdout ← IO.FS.Handle.mk output.getString .write
  let root ← Tactic.saveState
  let mut states : Array Tactic.SavedState := #[root]
  emit stdout <| jsonObj [("status", str "ready"), ("state_id", toJson (0 : Nat)),
    ("goals", ← snapshot)]
  repeat
    let line ← stdin.getLine
    if line.isEmpty then throwError "ProofLab session closed"
    let request := Json.parse line
    match request with
    | .error e => emit stdout <| jsonObj [("status", str "execution_error"), ("error", str e)]
    | .ok j =>
      let args := do pure (← fieldNat j "parent", ← fieldStr j "tactic")
      match args with
      | .error e => emit stdout <| jsonObj [("status", str "execution_error"), ("error", str e)]
      | .ok (parent, text) =>
        if h : parent < states.size then
          states[parent].restore
          try
            let stx ← match Parser.runParserCategory (← getEnv) `tactic text with
              | .ok stx => pure stx
              | .error e => throwError "{e}"
            -- Errors must throw, rather than use the editor's recovery behavior.
            Core.withCurrHeartbeats do
              withOptions (fun o => o.setNat `maxRecDepth 512) do
                withoutRecover <| evalTactic stx
                Term.synthesizeSyntheticMVarsNoPostponing
            let goals ← snapshot
            let id := states.size
            states := states.push (← Tactic.saveState)
            emit stdout <| jsonObj [("status", str "accepted"), ("state_id", toJson id),
              ("goals", goals)]
          catch e =>
            states[parent].restore
            emit stdout <| jsonObj [("status", str "invalid_candidate"),
              ("error", str (← e.toMessageData.toString))]
        else
          emit stdout <| jsonObj [("status", str "execution_error"),
            ("error", str "Unknown parent state")]

end ProofLab

open Lean Elab Command in
elab "#prooflab_audit " id:ident : command => do
  let name := id.getId
  let axioms ← liftCoreM <| Lean.collectAxioms name
  let allowed := [``propext, ``Classical.choice, ``Quot.sound]
  let forbidden := axioms.filter fun n => !allowed.contains n
  if !forbidden.isEmpty then
    throwError "ProofLab trust policy rejected axioms: {forbidden}"
  logInfo ("PROOFLAB_AUDIT:" ++ (Json.mkObj [
    ("declaration", toJson name.toString),
    ("axioms", toJson (axioms.map Name.toString)),
    ("verified", toJson true)]).compress)
