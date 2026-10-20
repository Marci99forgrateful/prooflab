import ProofLab.Bridge

/-! Native, elaborated expression trees for split auditing, not proof generation. -/
open Lean Meta Elab Command Term

namespace ProofLab

partial def expressionTree (e : Expr) : Json :=
  match e with
  | .bvar i => toJson #[toJson "var", toJson i]
  | .sort _ => toJson #[toJson "sort"]
  | .const n _ => toJson #[toJson "const", toJson n.toString]
  | .app f a => toJson #[toJson "app", expressionTree f, expressionTree a]
  | .forallE _ t b _ => toJson #[toJson "forall", expressionTree t, expressionTree b]
  | .lam _ t b _ => toJson #[toJson "lambda", expressionTree t, expressionTree b]
  | .letE _ t v b _ =>
      toJson #[toJson "let", expressionTree t, expressionTree v, expressionTree b]
  | .mdata _ b => expressionTree b
  | .proj n i b => toJson #[toJson "proj", toJson n.toString, toJson i, expressionTree b]
  | .lit (.natVal n) => toJson #[toJson "natural", toJson n]
  | .lit (.strVal s) => toJson #[toJson "string", toJson s]
  | .fvar _ => toJson #[toJson "UNEXPECTED_FREE_VARIABLE"]
  | .mvar _ => toJson #[toJson "UNEXPECTED_METAVARIABLE"]

end ProofLab

elab "#prooflab_structure " label:str " : " proposition:term : command => do
  let tree ← liftTermElabM do
    let e ← elabTerm proposition (some (mkSort Level.zero))
    synthesizeSyntheticMVarsNoPostponing
    let e ← instantiateMVars e
    let e ← withTransparency .reducible <| reduceAll e
    pure (ProofLab.expressionTree e)
  logInfo ("PROOFLAB_STRUCTURE:" ++ (Json.mkObj [
    ("id", toJson label.getString), ("tree", tree)]).compress)
