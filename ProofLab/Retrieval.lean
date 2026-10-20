import ProofLab.Bridge
import ProofLab.Structure

/-!
Independent bounded retrieval and read-only type probes. No third-party search
implementation is copied. Proof certification remains in the unchanged Bridge.
Every query restores the complete native tactic state; no proof step is executed.
-/
open Lean Meta Elab Tactic Command Term
namespace ProofLab.Retrieval

partial def containsHead (e : Expr) (name : Name) : Bool :=
  e.isConstOf name || match e with
    | .app f a => containsHead f name || containsHead a name
    | .forallE _ t b _ | .lam _ t b _ => containsHead t name || containsHead b name
    | .letE _ t v b _ => containsHead t name || containsHead v name || containsHead b name
    | .mdata _ b | .proj _ _ b => containsHead b name
    | _ => false


def moduleOf (name : Name) : CoreM String := do
  let env ← getEnv
  match env.getModuleIdxFor? name with
  | some idx => return (env.header.moduleNames[idx.toNat]!).toString
  | none => return "current environment"

def declaration (name : Name) : MetaM Json := do
  let info ← getConstInfo name
  let (args, bis, conclusion) ← forallMetaTelescope info.type
  let mut premises := #[]
  for arg in args do
    let typ ← inferType arg
    if ← isProp typ then premises := premises.push (← ppExpr typ).pretty
  return Json.mkObj [
    ("name", toJson name.toString), ("type", toJson (← ppExpr info.type).pretty),
    ("native_type", ProofLab.expressionTree info.type),
    ("source_module", toJson (← moduleOf name)),
    ("conclusion_head", toJson (conclusion.getAppFn.constName?.getD Name.anonymous).toString),
    ("parameters", toJson args.size), ("premises", toJson premises),
    ("implicit_parameters", toJson (bis.filter (· != .default)).size),
    ("instance_parameters", toJson (bis.filter (· == .instImplicit)).size)]

def probe (goal : MVarId) (name : Name) : MetaM Json := withoutModifyingState do
  let tick ← IO.monoNanosNow
  let hb ← IO.getNumHeartbeats
  let typ ← goal.getType
  let term ← mkConstWithFreshMVarLevels name
  let (args, bis, result) ← forallMetaTelescope (← inferType term)
  let mut compatible ← isDefEq result typ
  let mut missingInstances := 0
  if compatible then
    for arg in args, bi in bis do
      if bi == .instImplicit && !(← arg.mvarId!.isAssigned) then
        let type ← instantiateMVars (← inferType arg)
        match ← synthInstance? type with
        | some proofValue => arg.mvarId!.assign proofValue
        | none => missingInstances := missingInstances + 1
    if missingInstances > 0 then compatible := false
  let mut premises := #[]
  let mut unresolved := 0
  if compatible then
    for arg in args, bi in bis do
      unless ← arg.mvarId!.isAssigned do
        let type ← instantiateMVars (← inferType arg)
        if ← isProp type then
          premises := premises.push (← ppExpr type).pretty
        else if bi != .instImplicit then unresolved := unresolved + 1
  return Json.mkObj [
    ("tactic", toJson ("apply " ++ name.toString)), ("declaration", toJson name.toString),
    ("family", toJson "lemma"), ("compatible", toJson compatible),
    ("compatibility_kind", toJson "native conclusion unification plus available instance synthesis; not tactic execution"),
    ("premises", toJson premises), ("unresolved_explicit_data", toJson unresolved),
    ("missing_instances", toJson missingInstances),
    ("result_head", toJson (result.getAppFn.constName?.getD Name.anonymous).toString),
    ("elapsed_ns", toJson ((← IO.monoNanosNow) - tick)),
    ("heartbeats", toJson ((← IO.getNumHeartbeats) - hb))]

def rewriteProbe (goal : MVarId) (name : Name) (reverse : Bool) : MetaM Json :=
  withoutModifyingState do
    let tick ← IO.monoNanosNow
    let hb ← IO.getNumHeartbeats
    let mut compatible := false
    let mut target := ""
    let mut remaining := 0
    try
      let out ← goal.rewrite (← goal.getType) (← mkConstWithFreshMVarLevels name) reverse
      compatible := true
      target := (← ppExpr out.eNew).pretty
      remaining := out.mvarIds.length
    catch _ => pure ()
    return Json.mkObj [
      ("tactic", toJson ("rw [" ++ (if reverse then "← " else "") ++ name.toString ++ "]")),
      ("declaration", toJson name.toString), ("family", toJson "rewrite"),
      ("compatible", toJson compatible), ("rewritten_target", toJson target),
      ("rewrite_obligations", toJson remaining), ("reverse", toJson reverse),
      ("elapsed_ns", toJson ((← IO.monoNanosNow) - tick)),
      ("heartbeats", toJson ((← IO.getNumHeartbeats) - hb))]

def witnesses (goal : MVarId) : MetaM (Array Json × Nat) := withoutModifyingState do
  let target ← whnf (← goal.getType)
  unless target.getAppFn.isConstOf ``Exists do return (#[], 0)
  let expected := target.getAppArgs[0]!
  let mut terms : Array (Expr × String × Nat) := #[]
  let mut functions : Array Expr := #[]
  for d in ← getLCtx do
    unless d.isImplementationDetail || (← isProp d.type) do
      let t ← whnf d.type
      if t.isForall then functions := functions.push d.toExpr
      else if !t.isSort then terms := terms.push (d.toExpr, "in-scope term", 0)
  terms := terms.extract 0 12
  functions := functions.extract 0 6
  let mut constructions := 0
  for depth in [1:3] do
    let inputs := terms
    for f in functions do
      for (arg, _, d) in inputs do
        if constructions < 32 && d + 1 == depth then
          constructions := constructions + 1
          try
            let term ← withoutModifyingState <| mkAppM' f #[arg]
            if !term.hasExprMVar then
              let printed ← ppExpr term
              unless terms.any (fun (e, _, _) => e == term) do
                terms := terms.push (term, "typed function application: " ++ printed.pretty, depth)
          catch _ => pure ()
  if expected.getAppFn.isConstOf ``Prod then
    let inputs := terms.extract 0 8
    for (a, _, _) in inputs do
      for (b, _, _) in inputs do
        if constructions < 48 then
          constructions := constructions + 1
          try
            let pair ← withoutModifyingState <| mkAppM ``Prod.mk #[a,b]
            terms := terms.push (pair, "typed product construction", 1)
          catch _ => pure ()
  if expected.isConstOf ``Nat then
    terms := terms.push (mkNatLit 0, "bounded Nat literal", 0)
    terms := terms.push (mkNatLit 1, "bounded Nat literal", 0)
  let mut out := #[]
  for (term, construction, depth) in terms do
    let type ← inferType term
    let compatible ← withoutModifyingState <| isDefEq type expected
    let printed := (← ppExpr term).pretty
    out := out.push (Json.mkObj [
      ("tactic", toJson ("exists (" ++ printed ++ ")")), ("family", toJson "witness"),
      ("term", toJson printed), ("type", toJson (← ppExpr type).pretty),
      ("expected_type", toJson (← ppExpr expected).pretty),
      ("construction", toJson construction), ("construction_depth", toJson depth),
      ("compatible", toJson compatible)])
  return (out, constructions)

def query (names : Array String) : TacticM Json := do
  let saved ← Tactic.saveState
  let tick ← IO.monoNanosNow
  let hb ← IO.getNumHeartbeats
  try
    let goal ← getMainGoal
    goal.withContext do
      let mut rows := #[]
      let mut rewrites := 0
      for text in names.extract 0 128 do
        let name := text.toName
        try
          rows := rows.push (← probe goal name)
          if rewrites < 16 then
            let info ← getConstInfo name
            let (_,_,result) ← withoutModifyingState <| forallMetaTelescope info.type
            let eqArgs := result.getAppArgs
            let lhs := if eqArgs.size >= 3 then eqArgs[1]! else result
            let lhsHead := lhs.getAppFn.constName?.getD Name.anonymous
            if (result.isAppOf ``Eq || result.isAppOf ``Iff) && lhsHead != Name.anonymous &&
                containsHead (← goal.getType) lhsHead then
              for reverse in [false,true] do
                rows := rows.push (← rewriteProbe goal name reverse)
                rewrites := rewrites + 1
        catch e =>
          rows := rows.push <| Json.mkObj [("declaration", toJson text),
            ("family", toJson "probe_error"), ("error", toJson (← e.toMessageData.toString))]
      let (terms, constructions) ← witnesses goal
      let mut classes := #[]
      for d in ← getLCtx do
        unless d.isImplementationDetail do
          let head := (← whnf d.type).getAppFn.constName?.getD Name.anonymous
          if [``Group, ``CommGroup, ``Monoid, ``CommMonoid, ``CommRing, ``CommSemiring,
              ``Lattice, ``PartialOrder].contains head then classes := classes.push head.toString
      return Json.mkObj [("rows", toJson (rows ++ terms)), ("term_constructions", toJson constructions),
        ("declaration_probes", toJson (min 128 names.size)), ("rewrite_probes", toJson rewrites),
        ("classes", toJson classes), ("state", ← ProofLab.snapshot),
        ("elapsed_ns", toJson ((← IO.monoNanosNow) - tick)),
        ("heartbeats", toJson ((← IO.getNumHeartbeats) - hb))]
  finally saved.restore

end ProofLab.Retrieval

elab "#prooflab_declarations " names:str : command => do
  let rows ← liftTermElabM do
    let mut out := #[]
    for text in names.getString.splitOn "," do
      try
        let row ← withoutModifyingState <| ProofLab.Retrieval.declaration text.toName
        out := out.push row
      catch e => out := out.push <| Json.mkObj [("name", toJson text),
        ("error", toJson (← e.toMessageData.toString))]
    pure out
  logInfo ("PROOFLAB_INDEX:" ++ (toJson rows).compress)

elab "prooflab_retrieval_session" input:str output:str : tactic => do
  let stdin ← IO.FS.Handle.mk input.getString .read
  let stdout ← IO.FS.Handle.mk output.getString .write
  let root ← Tactic.saveState
  let mut states : Array Tactic.SavedState := #[root]
  ProofLab.emit stdout <| Json.mkObj [("status", toJson "ready"), ("state_id", toJson (0 : Nat)),
    ("goals", ← ProofLab.snapshot)]
  repeat
    let line ← stdin.getLine
    if line.isEmpty then throwError "ProofLab retrieval session closed"
    let j ← match Json.parse line with
      | .ok j => pure j
      | .error e => throwError "{e}"
    let parent ← match ProofLab.fieldNat j "parent" with
      | .ok parent => pure parent
      | .error e => throwError "{e}"
    if h : parent < states.size then
      states[parent].restore
      let requestTick ← IO.monoNanosNow
      let requestHeartbeats ← IO.getNumHeartbeats
      try
        let kind := (j.getObjValAs? String "kind").toOption.getD "step"
        if kind == "retrieve" then
          let names := (j.getObjValAs? (Array String) "names").toOption.getD #[]
          let result ← Core.withCurrHeartbeats <| ProofLab.Retrieval.query names
          ProofLab.emit stdout <| Json.mkObj [("status", toJson "retrieved"),
            ("state_id", toJson parent), ("retrieval", result)]
        else
          let text ← match ProofLab.fieldStr j "tactic" with
            | .ok text => pure text
            | .error e => throwError "{e}"
          let stx ← match Parser.runParserCategory (← getEnv) `tactic text with
            | .ok stx => pure stx
            | .error e => throwError "{e}"
          let actionTick ← IO.monoNanosNow
          let actionHeartbeats ← IO.getNumHeartbeats
          Core.withCurrHeartbeats do
            withOptions (fun o => o.setNat `maxRecDepth 512) do
              withoutRecover <| evalTactic stx
              Term.synthesizeSyntheticMVarsNoPostponing
          let goals ← ProofLab.snapshot
          let id := states.size
          states := states.push (← Tactic.saveState)
          ProofLab.emit stdout <| Json.mkObj [("status", toJson "accepted"),
            ("state_id", toJson id), ("goals", goals),
            ("native_elapsed_ns", toJson ((← IO.monoNanosNow) - actionTick)),
            ("native_heartbeats", toJson ((← IO.getNumHeartbeats) - actionHeartbeats))]
      catch e =>
        states[parent].restore
        ProofLab.emit stdout <| Json.mkObj [("status", toJson "invalid_candidate"),
          ("error", toJson (← e.toMessageData.toString)),
          ("native_elapsed_ns", toJson ((← IO.monoNanosNow) - requestTick)),
          ("native_heartbeats", toJson ((← IO.getNumHeartbeats) - requestHeartbeats))]
    else throwError "Unknown saved state"
