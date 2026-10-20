import ProofLab.Structure

/-! Offline diagnostics only. No state is merged or cached using this output.
The command elaborates a proposition and replays tactics without declaring a theorem.
Unresolved metavariables and full native expression representations remain visible.
-/
open Lean Meta Elab Command Term Tactic

elab "#prooflab_state " label:str " binders " count:num " : " proposition:term " := " script:str : command => do
  liftTermElabM do
    let type ← elabType proposition
    synthesizeSyntheticMVarsNoPostponing
    forallBoundedTelescope type (some count.getNat) fun _ target => do
      let root ← mkFreshExprMVar target
      let _ ← Elab.Tactic.run root.mvarId! do
        unless script.getString.isEmpty do
          let stx ← match Parser.runParserCategory (← getEnv) `tactic script.getString with
            | .ok stx => pure stx
            | .error e => throwError "{e}"
          withoutRecover <| evalTactic stx
          synthesizeSyntheticMVarsNoPostponing
        let mut goals := #[]
        for g in ← getUnsolvedGoals do
          let item ← g.withContext do
            let target ← instantiateMVars (← g.getType)
            let vars := (← getLCtx).getFVarIds
            let sequent ← mkForallFVars (vars.map mkFVar) target
            let reduced ← withTransparency .reducible <| reduceAll sequent
            pure <| Json.mkObj [
              ("goal_id", toJson g.name.toString),
              ("native_repr", toJson (reprStr sequent)),
              ("has_expr_mvar", toJson sequent.hasExprMVar),
              ("tree", ProofLab.expressionTree reduced)]
          goals := goals.push item
        logInfo ("PROOFLAB_STATE:" ++ (Json.mkObj [
          ("label", toJson label.getString), ("goals", toJson goals),
          ("use", toJson "diagnostic grouping only; not semantic state identity")]).compress)
      pure ()
