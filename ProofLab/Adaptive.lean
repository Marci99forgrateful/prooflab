import ProofLab.Retrieval

/-! Phase 6 bounded typed expression closure. Old retrieval/Bridge stay unchanged.
    Uses only current Lean context, inferred types and fresh saved-state probes. -/
open Lean Meta Elab Tactic Command Term
namespace ProofLab.Adaptive

partial def size (e : Expr) : Nat :=
  match e with
  | .app f a => 1 + size f + size a
  | .forallE _ t b _ | .lam _ t b _ => 1 + size t + size b
  | .letE _ t v b _ => 1 + size t + size v + size b
  | .mdata _ b | .proj _ _ b => 1 + size b
  | _ => 1

structure TermRow where
  expr : Expr
  depth : Nat
  derivation : String
  deriving Inhabited

partial def subterms (e : Expr) : Array Expr :=
  #[e] ++ match e with
  | .app f a => subterms f ++ subterms a
  | .mdata _ b | .proj _ _ b => subterms b
  | _ => #[]

partial def products (expected : Expr) (terms : Array TermRow) (fuel : Nat) : MetaM (Array TermRow × Nat) := do
  let mut found := #[]
  for r in terms do
    if found.size < 4 && (← withoutModifyingState <| isDefEq (← inferType r.expr) expected) then
      found := found.push r
  let e ← whnf expected
  let mut attempts := 0
  if fuel > 0 && e.getAppFn.isConstOf ``Prod then
    let args := e.getAppArgs
    let (left, lc) ← products args[0]! terms (fuel-1)
    let (right, rc) ← products args[1]! terms (fuel-1)
    attempts := lc + rc
    let mut localAttempts := 0
    for a in left do
      for b in right do
        if found.size < 4 && localAttempts < 4 && max a.depth b.depth < 3 then
          localAttempts := localAttempts + 1
          let term ← mkAppM ``Prod.mk #[a.expr,b.expr]
          unless found.any (fun r => r.expr == term) do
            found := found.push ⟨term, max a.depth b.depth + 1,
              "typed pair(" ++ (← ppExpr a.expr).pretty ++ ", " ++
              (← ppExpr b.expr).pretty ++ "); " ++ a.derivation ++ "; " ++ b.derivation⟩
    attempts := attempts + localAttempts
  return (found, attempts)

def witnesses (goal : MVarId) : MetaM (Array Json × Nat) := withoutModifyingState do
  let target ← whnf (← goal.getType)
  unless target.getAppFn.isConstOf ``Exists do return (#[], 0)
  let expected := target.getAppArgs[0]!
  let mut terms : Array TermRow := #[]
  for d in ← getLCtx do
    unless d.isImplementationDetail || (← isProp d.type) || d.type.isSort do
      if terms.size < 24 then
        terms := terms.push ⟨d.toExpr, 0, "in-scope typed term/function"⟩
  -- Intermediate expressions occurring in hypotheses are legitimate context data,
  -- not proof templates. Bound variables, proof expressions and sorts are excluded.
  for d in ← getLCtx do
    for e in (subterms d.type).extract 0 40 do
      if terms.size < 40 && !e.hasLooseBVars && !e.hasExprMVar && size e <= 64 then
        try
          let typ ← inferType e
          if !(← isProp typ) && !(← whnf typ).isSort &&
              !(terms.any (fun r => r.expr == e)) then
            terms := terms.push ⟨e, 0, "typed subexpression of a local hypothesis type"⟩
        catch _ => pure ()
  let mut attempts := 0
  for depth in [1:4] do
    let inputs := terms
    let mut branches := 0
    for f in inputs do
      let ft ← whnf (← inferType f.expr)
      if ft.isForall && branches < 24 then
        -- Do not spend expression closure on proposition-valued predicates.
        let dataResult ← forallTelescopeReducing ft fun _ result => pure (!result.isSort)
        if dataResult then
          branches := branches + 1
          for a in inputs do
            if attempts < (if expected.getAppFn.isConstOf ``Set then 64 else 96) &&
                terms.size < 64 && max f.depth a.depth + 1 == depth then
              attempts := attempts + 1
              try
                let term ← withoutModifyingState <| mkAppM' f.expr #[a.expr]
                let typ ← inferType term
                if !term.hasExprMVar && size term <= 64 && size typ <= 96 &&
                    !(← isProp typ) && !(terms.any (fun r => r.expr == term)) then
                  let desc := "application(" ++ (← ppExpr f.expr).pretty ++ ", " ++
                    (← ppExpr a.expr).pretty ++ "); parents: " ++ f.derivation ++ "; " ++ a.derivation
                  terms := terms.push ⟨term, depth, desc⟩
              catch _ => pure ()
  -- Set witnesses use explicit typed constructors, rather than treating a
  -- predicate as an ordinary callable or enumerating arbitrary set syntax.
  if expected.getAppFn.isConstOf ``Set then
    let inputs := terms
    for f in inputs do
      let ft ← whnf (← inferType f.expr)
      if ft.isForall then
        let dataResult ← forallTelescopeReducing ft fun _ result => pure (!result.isSort)
        if dataResult then
          for a in inputs do
            if (← inferType a.expr).getAppFn.isConstOf ``Set then
              for name in [``Set.image, ``Set.preimage] do
                if attempts < 96 && terms.size < 64 && max f.depth a.depth < 3 then
                  attempts := attempts + 1
                  try
                    let term ← withoutModifyingState <| mkAppM name #[f.expr,a.expr]
                    let typ ← inferType term
                    if !term.hasExprMVar && size term <= 64 && size typ <= 96 &&
                        !(terms.any (fun r => r.expr == term)) then
                      terms := terms.push ⟨term, max f.depth a.depth + 1,
                        "native " ++ name.toString ++ "(" ++ (← ppExpr f.expr).pretty ++
                        ", " ++ (← ppExpr a.expr).pretty ++ "); " ++ f.derivation ++
                        "; " ++ a.derivation⟩
                  catch _ => pure ()
  if expected.getAppFn.isConstOf ``Prod then
    let (pairs, count) ← products expected terms 3
    attempts := attempts + count
    terms := terms.extract 0 (64 - pairs.size) ++ pairs
  if expected.isConstOf ``Nat then
    terms := terms.push ⟨mkNatLit 0, 0, "bounded Nat literal"⟩
    terms := terms.push ⟨mkNatLit 1, 0, "bounded Nat literal"⟩
  let mut rows := #[]
  for r in terms do
    let typ ← inferType r.expr
    let compatible ← withoutModifyingState <| isDefEq typ expected
    if compatible then
      let text := (← ppExpr r.expr).pretty
      rows := rows.push <| Json.mkObj [
        ("tactic", toJson ("exists (" ++ text ++ ")")), ("family", toJson "witness"),
        ("term", toJson text), ("type", toJson (← ppExpr typ).pretty),
        ("expected_type", toJson (← ppExpr expected).pretty), ("compatible", toJson true),
        ("construction_depth", toJson r.depth), ("construction", toJson r.derivation),
        ("compatibility_kind", toJson "native inferred type unification; not tactic acceptance")]
  return (rows, attempts)

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
          rows := rows.push (← ProofLab.Retrieval.probe goal name)
          if rewrites < 16 then
            let info ← getConstInfo name
            let (_,_,result) ← withoutModifyingState <| forallMetaTelescope info.type
            let eqArgs := result.getAppArgs
            let lhs := if eqArgs.size >= 3 then eqArgs[1]! else result
            let lhsHead := lhs.getAppFn.constName?.getD Name.anonymous
            if (result.isAppOf ``Eq || result.isAppOf ``Iff) && lhsHead != Name.anonymous &&
                ProofLab.Retrieval.containsHead (← goal.getType) lhsHead then
              for reverse in [false,true] do
                rows := rows.push (← ProofLab.Retrieval.rewriteProbe goal name reverse)
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
        ("synthesis_limits", toJson "depth=3; functions/stage=24; initial locals=24; terms=64; application attempts=96; total with pairs=128; expression nodes=64; type nodes=96"), ("classes", toJson classes), ("state", ← ProofLab.snapshot),
        ("elapsed_ns", toJson ((← IO.monoNanosNow) - tick)),
        ("heartbeats", toJson ((← IO.getNumHeartbeats) - hb))]
  finally saved.restore

end ProofLab.Adaptive

elab "prooflab_adaptive_session" input:str output:str : tactic => do
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
          let result ← Core.withCurrHeartbeats <| ProofLab.Adaptive.query names
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
