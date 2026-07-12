---
title: "Deterministic Replay Monoid Homomorphism and Induction Proof"
kind: "pdf"
source_pdf: "Deterministic_Replay___Monoid_Homomorphism_and_Induction_Proof.pdf"
---

# Deterministic Replay Monoid Homomorphism and Induction Proof

Original PDF: [Deterministic_Replay___Monoid_Homomorphism_and_Induction_Proof.pdf](../pdf/Deterministic_Replay___Monoid_Homomorphism_and_Induction_Proof.pdf)

## Page 1

Deterministic Replay: Monoid Homomorphism and
Induction Proof
Definition 0.1 (State space). Let B = {0,1}. Let Σ denote the system
state space (finite or otherwise well-typed).
Definition 0.2 (Events, event monoid). Let T be a finite set of transi-
tion labels and let I be the set of input tokens (including recorded external
responses, binding/router identifiers, timestamps, etc.). Define the event set
E := T ×I ×M,
where M is an environment metadata space. The free monoid E∗ consists of
all finite sequences (strings) of events with concatenation · and empty word
ε.
Definition 0.3 (Endomorphism monoid). Let End(Σ) denote the monoid
of endomorphisms on Σ under composition ◦, with identity id .
Σ
Definition 0.4 (Per-event semantics). For each transition label τ ∈ T de-
fine a pure transition function
ϕ : Σ×I ×R×M → Σ,
τ
where R denotes a deterministic random-output domain (the PRNG output
space). For an event e = (τ,i,η) ∈ E and a PRNG sample r ∈ R the
per-event endomorphism is
F(e;r) : Σ → Σ, F(e;r)(σ) := ϕ (σ,i,r,η).
τ
Definition 0.5 (Telemetry record). A telemetry record is a tuple R =
(g,s,w,∆) where
• g is a GUID trace identifier,
• s is a cryptographic seed (integer),
• w = e e ...e ∈ E∗ is the ordered event log,
1 2 n
• ∆ is an optional set of snapshot state(s) (checkpoint(s)).
Associated to seed s and a deterministic PRNG is a sequence of outputs
(r ,r ,...).
1 2
1

## Page 2

Assumption 0.6 (Completeness of recorded nondeterminism). All sources
of nondeterminism present in the original execution are either:
1. explicitly recorded in w or ∆, or
2. deterministically derivable from the seed s via the PRNG.
Assumption 0.7 (Purity of replay semantics). During replay, the bind-
ing implementations used to compute ϕ are pure functions of their explicit
τ
inputs: prior state, input token, PRNG output, and environment meta-
data. Externalsideeffectsarereplacedbyrecordedresponsesordeterministic
stubs.
Definition 0.8 (ExtensionofF tosequences). Fix a record R = (g,s,w,∆)
and PRNG outputs (r ,r ,...,r ). For event e define F(e ) := F(e ;r ) ∈
1 2 n j j j j
End(Σ). Extend F multiplicatively to sequences by
F(e e ···e ) := F(e )◦F(e )◦···◦F(e ).
1 2 n n n−1 1
By convention, F(ε) := id .
Σ
Lemma 0.9 (Monoid homomorphism). The map
F : (E∗,·,ε) −→ (End(Σ),◦,id )
Σ
defined above is a monoid homomorphism: for all u,v ∈ E∗,
F(u·v) = F(v)◦F(u), F(ε) = id .
Σ
Proof. Immediate from the definition. The empty word maps to identity by
definition. Concatenation u·v corresponds to the sequential application of
event endomorphisms; by definition of composition ordering we have F(u·
v) = F(v)◦F(u). Hence F preserves the monoid structure.
Theorem0.10(DeterministicReplay—formalstatement). LetR = (g,s,w,∆)
be a telemetry record satisfying the stated assumptions. Let w = e e ···e
1 2 n
and let (r ,...,r ) be the PRNG outputs deterministically generated from
1 n
seed s according to the agreed indexing convention. Then there exists a de-
terministic replay procedure Replay(R) that reconstructs the unique state
sequence
σ − e →1 σ − e →2 ··· − e →n σ ,
0 1 n
where σ = F(e ···e )(σ ) and σ equals the snapshot in ∆ (if provided) or
j 1 j 0 0
the canonical initial state.
Proof. We prove by induction on n = |w| that replay reconstructs the same
states as the original execution.
2

## Page 3

Base case (n = 0). If w = ε then F(w) = id and the replayed state
Σ
sequenceisthesingleton{σ }whereσ isthesnapshotin∆(orthecanonical
0 0
initial state). Equality with the original trivially holds.
Inductive hypothesis. Assume for some k ≥ 0 that for any telemetry
record whose event log length is k the replay procedure reconstructs the
original states σ ,σ ,...,σ satisfying
0 1 k
σ = F(e ···e )(σ ) for 0 ≤ j ≤ k.
j 1 j 0
Inductive step (k → k +1). Consider a record with w = e ···e e
1 k k+1
and associated PRNG outputs (r ,...,r ). By the inductive hypothesis,
1 k+1
replaying the prefix e ···e produces the state σ = F(e ···e )(σ ). For
1 k k 1 k 0
step k+1 the replay computes
σ′ := F(e ;r )(σ ),
k+1 k+1 k+1 k
where F(e ;r ) is the per-event endomorphism computed with the
k+1 k+1
recorded input token, environment metadata, and the PRNG output r .
k+1
By the assumptions:
• the PRNG output r equals the original run’s r (determinism of
k+1 k+1
PRNG given seed s),
• the input token and environment metadata match the original values
(they are recorded),
• the per-event function ϕ is pure and deterministic for the given
τ
k+1
arguments.
Thus σ′ = σ , where σ is the state the original execution produced
k+1 k+1 k+1
after event e . This completes the inductive step.
k+1
Therefore,bymathematicalinduction,replayreconstructsthesamestate
sequence for all n.
Corollary 0.11 (Closureunderconcatenation). If R = (g ,s ,w ,∆ ) and
1 1 1 1 1
R = (g ,s ,w ,∆ ) are replayable traces and the concatenation w ·w is
2 2 2 2 2 1 2
provided with a consistent PRNG indexing scheme (or equivalent combined
seed), then the concatenated trace is replayable and
F(w ·w ) = F(w )◦F(w ).
1 2 2 1
3

## Page 4

Remark 0.12 (Practical caveats). The theorem is only valid under the
stated assumptions. In practice, ensure:
• explicit recording of external responses and wall-clock values if they
influence ϕ ;
τ
• deterministichandling(orrecording)ofconcurrencyinterleavings(vec-
tor clocks, global counters, or total-order logs);
• PRNGoutputsareindexedand/orrecordedsothemappingeventindex
(cid:55)→ r is unambiguous.
j
Failure to observe these requirements yields partial or no reproducibility.
4
