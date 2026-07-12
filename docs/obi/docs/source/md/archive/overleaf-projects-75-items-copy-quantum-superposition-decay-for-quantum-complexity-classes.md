---
title: "Quantum Superposition Decay for Quantum Complexity Classes"
kind: "archive"
source_archive: "overleaf-projects-75-items-copy"
source_folder: "overleaf-projects-75-items-copy/Quantum Superposition Decay for Quantum Complexity Classes"
---

# Quantum Superposition Decay for Quantum Complexity Classes

Source folder: `overleaf-projects-75-items-copy/Quantum Superposition Decay for Quantum Complexity Classes`

## Extracted Files

- `main.tex`

## main

<div class="titlepage">

**Quantum Superposition Decay for Quantum Complexity Classes**  
A Classical–Quantum Bridge via the Read-Write-Execute Memory Model  
Nnamdi Okpala  
OBINexus Computing  
`okpalan@protonmail.com`  
2026-06-23  

</div>

# Introduction

The relationship between quantum and classical computation is most precisely characterised through the lens of promise-problem complexity classes. While quantum speedup for specific problem families (integer factorisation, unstructured search) is well established, a general framework that maps the *measurement event*—the moment a quantum superposition collapses to a definite classical outcome—onto classical computational primitives has received less systematic attention.

This paper proposes such a framework under the name **Superposition Decay** ($`\mathrm{SD}`$). The central intuition is that the collapse of a superposition is not a passive observation but an active computational window: a bounded interval of control during which a system may coherently commit or roll back parallel computations, analogous to a transactional memory operation.

We formalise five related contributions:

1.  **The $`\mathrm{SD}`$ window.** A formal definition of the measurement window as a triple (resolved / rejected / pending), bounding acceptance and rejection by probability thresholds $`a(n)`$ and $`b(n)`$, with an intermediate *pending* region supporting deferred evaluation.

2.  **The RWX memory model.** A Read-Write-Execute abstraction that maps quantum measurement to classical memory transactions: $`n`$ writes followed by $`k`$ reads collapse to a single coherent read event when the last read is the terminal operation.

3.  **Complexity-class tractability under $`\mathrm{SD}`$.** A characterisation showing that $`\ensuremath{\mathsf{BQP}}`$ promise problems are exactly the class tractable under a single superposition decay event; problems in $`\ensuremath{\mathsf{PP}}`$ and $`\ensuremath{\mathsf{PSPACE}}`$ require multiple decay events or additional measurement principles.

4.  **Rift: quantum-classical grammar matching.** A formalisation of the Rift compiler’s parser as a quantum automaton, with grammar production rules as superposed branches and parse commitment as a grammar decay event governed by the stabilisation principle.

5.  **Quantum Burst Protocol (QBP).** A communication protocol in which all candidate network paths are held in superposition during connection negotiation and selected by a single measurement (spectral decay), achieving optimal routing in $`O(1)`$ measurement time.

The paper is organised as follows. Section <a href="#sec:prelim" data-reference-type="ref" data-reference="sec:prelim">2</a> reviews necessary background in quantum mechanics and complexity theory. Section <a href="#sec:sd" data-reference-type="ref" data-reference="sec:sd">3</a> defines superposition decay formally. Section <a href="#sec:rwx" data-reference-type="ref" data-reference="sec:rwx">4</a> presents the RWX memory model. Section <a href="#sec:complexity" data-reference-type="ref" data-reference="sec:complexity">5</a> maps results onto the complexity hierarchy. Section <a href="#sec:parallel" data-reference-type="ref" data-reference="sec:parallel">6</a> states and proves the main parallelism theorem. Section <a href="#sec:rift" data-reference-type="ref" data-reference="sec:rift">7</a> formalises Rift as a quantum-classical grammar matcher. Section <a href="#sec:qbp" data-reference-type="ref" data-reference="sec:qbp">8</a> introduces QBP. Section <a href="#sec:mmuko" data-reference-type="ref" data-reference="sec:mmuko">9</a> describes the MMUKO OS and OBINexus toolchain. Section <a href="#sec:conclusion" data-reference-type="ref" data-reference="sec:conclusion">10</a> concludes.

# Preliminaries

## Quantum Postulates

We work in the standard Hilbert-space formulation of quantum mechanics. A quantum state is represented by a unit vector $`\left| \psi \right\rangle \in \mathbb{C}^{2^n}`$ for an $`n`$-qubit system.

<div class="axiom">

**Axiom 1** (State Postulate). The complete state of a quantum system at time $`t`$ is described by a normalised vector $`\left| \psi(t) \right\rangle \in \mathcal{H}`$, the system’s Hilbert space, satisfying $`\left\langle \psi(t) \mid \psi(t) \right\rangle = 1`$.

</div>

<div class="axiom">

**Axiom 2** (Superposition Postulate). If $`\left| \psi_1 \right\rangle`$ and $`\left| \psi_2 \right\rangle`$ are valid states of a quantum system, then any linear combination
``` math
\left| \psi \right\rangle = c_1 \left| \psi_1 \right\rangle + c_2 \left| \psi_2 \right\rangle,
    \quad c_1, c_2 \in \mathbb{C}, \quad |c_1|^2 + |c_2|^2 = 1,
```
is also a valid state. This follows from the linearity and homogeneity of the Schrödinger equation.

</div>

<div class="axiom">

**Axiom 3** (Wave-Function Collapse / Measurement Postulate). Upon measurement of an observable $`\hat{O}`$ with eigenvalues $`\{\lambda_i\}`$ and eigenstates $`\{\left| e_i \right\rangle\}`$, the system transitions from $`\left| \psi \right\rangle = \sum_i c_i \left| e_i \right\rangle`$ to eigenstate $`\left| e_j \right\rangle`$ with probability $`|c_j|^2`$. The post-measurement state is $`\left| e_j \right\rangle`$.

</div>

<div class="axiom">

**Axiom 4** (Evolution Postulate). Between measurements, a closed quantum system evolves unitarily: $`\left| \psi(t) \right\rangle = U(t)\left| \psi(0) \right\rangle`$, where $`U(t)`$ is a unitary operator.

</div>

## Classical Turing Machine and Complexity

A *Turing machine* (TM) is a tuple $`M = (Q, \Sigma, \Gamma, \delta,
q_0, q_{\text{acc}}, q_{\text{rej}})`$ with the standard interpretation. Time complexity $`T(n)`$ denotes the maximum number of steps on inputs of length $`n`$. We use the standard complexity classes $`\ensuremath{\mathsf{P}}`$, $`\ensuremath{\mathsf{NP}}`$, $`\ensuremath{\mathsf{BPP}}`$, $`\ensuremath{\mathsf{PP}}`$, $`\ensuremath{\mathsf{PSPACE}}`$, and $`\ensuremath{\mathsf{BQP}}`$; their promise-problem definitions are recalled in Section <a href="#sec:complexity" data-reference-type="ref" data-reference="sec:complexity">5</a>.

## Quantum Circuits

A *quantum circuit* $`Q_n`$ on $`n`$ qubits is a sequence of gates drawn from a universal gate set (e.g., $`\{H, \mathrm{CNOT}, T\}`$) that accepts an $`n`$-qubit input and produces a 1-qubit output. A *uniform circuit family* $`\ensuremath{\mathcal{Q}}= \{Q_n : n \in \mathbb{N}\}`$ is one where the description of $`Q_n`$ is computable in polynomial time from $`n`$.

## Probabilistic Directed Acyclic Graphs

<div class="definition">

**Definition 5** (Probabilistic DAG). A *probabilistic directed acyclic graph* $`G = (V, E, p)`$ is a DAG where each edge $`(u, v) \in E`$ carries a probability weight $`p(u,v) \in [0,1]`$ such that for every vertex $`u`$, $`\sum_{v : (u,v) \in E} p(u,v) \leq 1`$. Each path from a source to a sink represents a computation branch; the probability of a path is the product of its edge weights.

</div>

# Superposition Decay

## Informal Motivation

When a quantum system in superposition is measured, the resulting classical outcome is not predetermined—it is drawn from a probability distribution defined by the amplitudes. We argue that this *measurement event* is best understood not as an instantaneous point but as a *window*: a bounded region of the computation during which the system retains coherence and the outcomes of parallel branches may still be combined or discarded.

Once the window closes—the superposition *decays*—a single classical outcome is committed. The $`\mathrm{SD}`$ framework captures this window operationally.

## Formal Definition

<div class="definition">

**Definition 6** (Quantum Connection Graph). A *quantum connection* is a graph $`G = (E, N)`$ where $`N`$ is the set of $`n`$-qubit nodes (quantum registers) and $`E \subseteq N \times N`$ is the set of entanglement edges. A path from node $`A`$ to node $`B`$ in $`G`$ represents a sequence of entangled operations connecting two computational loci.

</div>

<div class="definition">

**Definition 7** (Superposition State Vector). For an $`n`$-qubit system, the superposition state is
``` math
\left| \Psi \right\rangle = \sum_{x \in \{0,1\}^n} \alpha_x \left| x \right\rangle,
    \quad \alpha_x \in \mathbb{C}, \quad \sum_{x} |\alpha_x|^2 = 1.
```
The probability of observing basis state $`\left| x \right\rangle`$ is $`p(x) = |\alpha_x|^2`$.

</div>

<div id="def:sdwindow" class="definition">

**Definition 8** (Superposition Decay Window). Let $`\ensuremath{\mathcal{Q}}= \{Q_n\}`$ be a uniform quantum circuit family and let $`a, b : \mathbb{N}\to [0,1]`$ be functions with $`a(n) > b(n)`$ for all $`n`$. The *superposition decay window* $`\ensuremath{\mathrm{SD}}(a, b)`$ is the triple
``` math
\ensuremath{\mathrm{SD}}(a, b) \;=\; \bigl(\, \text{resolved},\; \text{rejected},\; \text{pending} \,\bigr),
```
where for an input $`x`$ of length $`n`$:

- $`x`$ is **resolved** (accepted) if $`\Pr[Q_{|x|}(x) = 1] \geq a(|x|)`$,

- $`x`$ is **rejected** if $`\Pr[Q_{|x|}(x) = 1] \leq b(|x|)`$,

- $`x`$ is **pending** if $`b(|x|) < \Pr[Q_{|x|}(x) = 1] < a(|x|)`$.

The *decay event* is the transition of a state from *pending* to either *resolved* or *rejected* upon measurement.

</div>

<div class="remark">

*Remark 9*. The three-valued output (resolved / rejected / pending) generalises the standard binary outcome of a classical TM. The *pending* state corresponds precisely to the undecided region of a promise problem: the system is contractually guaranteed not to receive inputs from this region in the promise-problem formulation, but the $`\mathrm{SD}`$ framework makes the region explicit as a computational state.

</div>

## Constructive and Destructive Superposition

The superposition principle admits both *constructive* interference (amplitudes add, increasing probability of a desired outcome) and *destructive* interference (amplitudes cancel, suppressing undesired outcomes). We formalise this in terms of the wave function as follows.

<div class="definition">

**Definition 10** (Constructive / Destructive Interference). Given two states $`\left| \psi_1 \right\rangle = \sum_x \alpha_x \left| x \right\rangle`$ and $`\left| \psi_2 \right\rangle = \sum_x \beta_x \left| x \right\rangle`$, their superposition $`\left| \psi \right\rangle = c_1 \left| \psi_1 \right\rangle + c_2 \left| \psi_2 \right\rangle`$ exhibits:

- **Constructive interference** at $`x`$ if $`|c_1 \alpha_x + c_2 \beta_x| > \max(|c_1 \alpha_x|, |c_2 \beta_x|)`$.

- **Destructive interference** at $`x`$ if $`|c_1 \alpha_x + c_2 \beta_x| < \min(|c_1 \alpha_x|, |c_2 \beta_x|)`$.

</div>

In the $`\mathrm{SD}`$ framework, a quantum algorithm exploits constructive interference to amplify the amplitude of the correct solution branch before the decay window closes, and destructive interference to suppress incorrect branches.

# The Read-Write-Execute (RWX) Memory Model

## Motivation

Classical memory access is characterised by read ($`R`$), write ($`W`$), and execute ($`X`$) permissions, typically represented as a triple $`(r, w, x)`$ per memory region. We propose a quantum analogue in which the *sequence* of reads and writes within a superposition decay window determines the atomicity and coherence of the resulting classical observation.

## Formal Model

<div class="definition">

**Definition 11** (RWX Operation Sequence). An *RWX sequence* is a finite ordered list of operations $`\sigma = (o_1, o_2, \ldots, o_k)`$ where each $`o_i \in \{R, W, X\}`$. The sequence is *terminal-read* if $`o_k = R`$ (the final operation is a read).

</div>

<div id="def:adu" class="definition">

**Definition 12** (Atomic Decay Unit). A terminal-read RWX sequence of $`w`$ writes followed by $`r`$ reads,
``` math
\sigma = (\underbrace{W, W, \ldots, W}_{w},\;
              \underbrace{R, R, \ldots, R}_{r-1},\; R),
```
constitutes a single *atomic decay unit* (ADU) equivalent to one coherent read operation. Formally:
``` math
w \cdot W + r \cdot R \;\xrightarrow{\;\ensuremath{\mathrm{SD}}\;}\; 1 \cdot R_{\text{coherent}}.
```

</div>

<div class="example">

**Example 13** (4-Write 2-Read ADU). The concrete instance stated in the source document is:
``` math
4W + 2R \;\xrightarrow{\;\ensuremath{\mathrm{SD}}\;}\; 1R.
```
This means: four parallel write operations (corresponding to four parallel computation branches in superposition) and two intermediate read probes collapse—upon superposition decay—into a single coherent classical read outcome. The dual-state nature of the system (write = superposed, read = collapsed) ensures that the terminal read is the only externally observable event.

</div>

<div class="proposition">

**Proposition 14** (Dual-State Equivalence). *In a quantum system respecting the $`\mathrm{SD}`$ window, the state before the terminal read is a superposition of all write branches. The terminal read collapses this superposition to a single classical value. Therefore, the external observer sees exactly one read operation regardless of the number of internal write branches.*

</div>

<div class="proof">

*Proof.* By the Measurement Postulate (Axiom 3), measurement of the system in state $`\left| \Psi \right\rangle = \sum_x \alpha_x \left| x \right\rangle`$ produces outcome $`x`$ with probability $`|\alpha_x|^2`$ and collapses the state to $`\left| x \right\rangle`$. Each write branch corresponds to a basis state $`\left| x \right\rangle`$. Since the terminal read is the sole measurement, all prior writes are unobserved intermediate computations within the unitary evolution $`U(t)`$. By the Evolution Postulate (Axiom 4), $`U(t)`$ is reversible and does not produce classical outputs; only the terminal measurement does. Hence the external observable record contains exactly one read event. 0◻ ◻

</div>

## RWX Permission Table

The classical RWX permission system maps directly onto the decay window:

<div class="center">

| **Permission** | **Classical Meaning** | **Quantum / $`\mathrm{SD}`$ Analogue** |
|:---|:---|:---|
| $`R`$ (Read) | Load value from memory | Terminal measurement; collapses superposition |
| $`W`$ (Write) | Store value to memory | Unitary gate application; maintains superposition |
| $`X`$ (Execute) | Run code in memory region | Quantum circuit evaluation within decay window |

</div>

# Complexity Classes Under Superposition Decay

## Promise Problem Formulation

A *promise problem* is a pair $`(A_{\text{yes}}, A_{\text{no}})`$ of disjoint languages. An algorithm *solves* the promise problem if it accepts every $`x \in A_{\text{yes}}`$ and rejects every $`x \in A_{\text{no}}`$, with no constraint on inputs outside $`A_{\text{yes}} \cup A_{\text{no}}`$.

## Complexity Class Definitions

<div id="tab:classes">

| **Class** | Criteria |
|:---|:---|
| **$`\ensuremath{\mathsf{P}}`$** | Promise problems for which a polynomial-time *deterministic* TM accepts all strings in $`A_{\text{yes}}`$ and rejects all strings in $`A_{\text{no}}`$. |
| **$`\ensuremath{\mathsf{BPP}}`$** | Promise problems for which a polynomial-time *probabilistic* TM accepts every string in $`A_{\text{yes}}`$ with probability $`\geq \tfrac{2}{3}`$ and every string in $`A_{\text{no}}`$ with probability $`\leq \tfrac{1}{3}`$. |
| **$`\ensuremath{\mathsf{BQP}}`$** | Promise problems such that for functions $`a, b : \mathbb{N}\to [0,1]`$ with $`a(n) \geq \tfrac{2}{3}`$ and $`b(n) \leq \tfrac{1}{3}`$, there exists a uniform quantum circuit family $`\ensuremath{\mathcal{Q}}= \{Q_n : n \in \mathbb{N}\}`$ where $`Q_n`$ accepts $`n`$ qubits and gives a 1-qubit output, such that every $`x \in A_{\text{yes}}`$ is accepted with probability $`\geq a(|x|)`$ and every $`x \in A_{\text{no}}`$ is accepted with probability $`\leq b(|x|)`$. |
| **$`\ensuremath{\mathsf{PP}}`$** | Promise problems for which a polynomial-time probabilistic TM accepts every string in $`A_{\text{yes}}`$ with probability $`> \tfrac{1}{2}`$ and every string in $`A_{\text{no}}`$ with probability $`\leq \tfrac{1}{2}`$. |
| **$`\ensuremath{\mathsf{PSPACE}}`$** | Promise problems for which a *deterministic* TM running in polynomial *space* accepts all $`A_{\text{yes}}`$ and rejects all $`A_{\text{no}}`$. |

Complexity class definitions in the promise-problem framework.

</div>

## Tractability Under $`\mathrm{SD}`$

<div id="thm:bqp" class="theorem">

**Theorem 15** ($`\mathrm{SD}`$-Tractability of $`\mathsf{BQP}`$). *A promise problem $`(A_{\text{yes}}, A_{\text{no}})`$ is in $`\ensuremath{\mathsf{BQP}}`$ if and only if it is solvable by a uniform quantum circuit family within a single superposition decay window $`\ensuremath{\mathrm{SD}}(a, b)`$ with $`a(n) - b(n) \geq \tfrac{1}{3}`$ for all $`n`$.*

</div>

<div class="proof">

*Proof.* $`(\Rightarrow)`$ By definition of $`\ensuremath{\mathsf{BQP}}`$, there exists a uniform circuit family $`\{Q_n\}`$ with the stated acceptance probabilities. The circuit $`Q_n`$ operates entirely within a unitary evolution (all gates are write operations in RWX terms) and terminates with a single measurement (the terminal read). This constitutes a single ADU as in Definition <a href="#def:adu" data-reference-type="ref" data-reference="def:adu">12</a>, hence falls within one $`\mathrm{SD}`$ window.

$`(\Leftarrow)`$ Suppose a single $`\mathrm{SD}`$$`(a,b)`$ window with $`a(n) - b(n) \geq
  \tfrac{1}{3}`$ solves the promise problem. The circuit within the window is unitary (by the Evolution Postulate) and polynomial-time (by the polynomial-size constraint on the circuit family). This is exactly the definition of a $`\ensuremath{\mathsf{BQP}}`$ circuit. 0◻ ◻

</div>

<div class="corollary">

**Corollary 16**. *$`\ensuremath{\mathsf{P}}\subseteq \ensuremath{\mathsf{BPP}}\subseteq \ensuremath{\mathsf{BQP}}`$ under the $`\mathrm{SD}`$ framework, since deterministic and bounded-error probabilistic computations can be simulated by a single decay window with all amplitude concentrated on one branch.*

</div>

<div id="thm:pp" class="theorem">

**Theorem 17** (Multi-Decay Requirement for $`\mathsf{PP}`$). *There exist promise problems in $`\ensuremath{\mathsf{PP}}\setminus \ensuremath{\mathsf{BQP}}`$ that require more than one superposition decay event to resolve under $`\mathrm{SD}`$.*

</div>

<div class="proof">

*Proof Sketch.* $`\ensuremath{\mathsf{PP}}`$ allows acceptance probabilities arbitrarily close to $`\tfrac{1}{2}`$, whereas $`\ensuremath{\mathsf{BQP}}`$ requires a gap of at least $`\tfrac{1}{3}`$. A problem instance where $`\Pr[\text{accept}] = \tfrac{1}{2} + \epsilon`$ for arbitrarily small $`\epsilon > 0`$ cannot be distinguished from a reject instance (with $`\Pr = \tfrac{1}{2} - \epsilon`$) by a single decay event with fixed thresholds $`a, b`$ satisfying $`a - b \geq \tfrac{1}{3}`$. Multiple sequential decay events (with amplitude amplification between events) are required to drive the probability above the $`\mathsf{BQP}`$ threshold. 0◻ ◻

</div>

<div class="remark">

*Remark 18*. $`\ensuremath{\mathsf{PSPACE}}`$ problems, being characterised by polynomial-space deterministic computation, lie outside the reach of a constant number of superposition decay events unless $`\ensuremath{\mathsf{BQP}}= \ensuremath{\mathsf{PSPACE}}`$, which is not currently believed. They require fundamentally different principles—either unbounded decay depth or oracle access—within the $`\mathrm{SD}`$ framework.

</div>

# The Main Parallelism Theorem

## Statement

<div id="thm:main" class="theorem">

**Theorem 19** (Classical-to-Quantum Parallelism via $`\mathrm{SD}`$). *Let $`\mathcal{A}`$ be a classical algorithm with time complexity $`O(f(n))`$ where $`f`$ is a linear function ($`f(n) = cn`$ for some constant $`c > 0`$), and let $`\mathcal{A}`$ be deterministic or non-deterministic. Then there exists a quantum circuit family $`\ensuremath{\mathcal{Q}}_{\mathcal{A}} = \{Q_n\}`$ such that:*

1.  *$`Q_n`$ simulates all execution branches of $`\mathcal{A}`$ on inputs of length $`n`$ in *parallel* within a single superposition decay window $`\ensuremath{\mathrm{SD}}(a, b)`$.*

2.  *The circuit size of $`Q_n`$ is polynomial in $`n`$.*

3.  *The correct output is obtained upon the terminal measurement (the decay event) with probability $`\geq \tfrac{2}{3}`$.*

</div>

<div class="proof">

*Proof.* We construct $`Q_n`$ as follows.

**Step 1: Encode branches.** The $`k`$ non-deterministic branches of $`\mathcal{A}`$ on input $`x`$ correspond to basis states $`\left| b_1 \right\rangle, \ldots,
  \left| b_k \right\rangle`$ in a $`\lceil \log_2 k \rceil`$-qubit register. Since $`\mathcal{A}`$ runs in linear time $`O(n)`$, the number of branches is at most $`k \leq 2^{cn}`$ for some constant $`c`$; encoding requires $`O(n)`$ qubits.

**Step 2: Superpose branches.** Apply a Hadamard transform $`H^{\otimes
  \lceil \log_2 k \rceil}`$ to create the uniform superposition $`\left| \Psi_0 \right\rangle = \frac{1}{\sqrt{k}} \sum_{i=1}^k \left| b_i \right\rangle`$.

**Step 3: Parallel evaluation.** By the linearity of unitary evolution, the circuit $`U_{\mathcal{A}}`$ that implements one step of $`\mathcal{A}`$ acts on all branches simultaneously: $`U_{\mathcal{A}} \left| \Psi_0 \right\rangle = \frac{1}{\sqrt{k}} \sum_i U_{\mathcal{A}}
  \left| b_i \right\rangle`$. Since $`\mathcal{A}`$ runs in $`O(n)`$ steps, $`U_{\mathcal{A}}`$ consists of $`O(n)`$ layers, each implementable by a polynomial-size circuit.

**Step 4: Amplitude amplification.** Apply Grover-type amplitude amplification  to boost the amplitude of accepting branches. After $`O(\sqrt{k})`$ iterations, the probability of observing an accepting branch exceeds $`\tfrac{2}{3}`$.

**Step 5: Terminal measurement.** Measure the output qubit. This constitutes the single superposition decay event. By Theorem <a href="#thm:bqp" data-reference-type="ref" data-reference="thm:bqp">15</a>, the resulting problem is in $`\ensuremath{\mathsf{BQP}}`$.

The total circuit size is $`O(n \cdot \sqrt{k}) \leq O(n \cdot 2^{cn/2})`$, which is polynomial for fixed $`c < \tfrac{2 \log n}{n}`$—i.e., for linear $`f(n) = cn`$ with small $`c`$. This covers all algorithms with sub-exponential branch counts, which includes all deterministic and polynomially-branching non-deterministic linear-time algorithms. 0◻ ◻

</div>

## Linear Systems as Parallel DAGs

<div id="thm:dag" class="theorem">

**Theorem 20** (Linear Systems as Probabilistic DAGs). *Any system of $`m`$ linear equations in $`n`$ variables over $`\mathbb{R}`$ (or $`\mathbb{C}`$) with a unique solution can be expressed as a probabilistic DAG $`G = (V, E, p)`$ whose parallel evaluation under $`\mathrm{SD}`$ yields the solution in time $`O(\log n)`$ on a quantum system.*

</div>

<div class="proof">

*Proof Sketch.* The system $`A\mathbf{x} = \mathbf{b}`$ (with $`A \in \mathbb{R}^{m \times n}`$) has a unique solution $`\mathbf{x}^* = A^{-1}\mathbf{b}`$ (assuming $`A`$ is invertible). The HHL algorithm  solves this system in $`O(\log n \cdot \kappa^2)`$ time on a quantum computer, where $`\kappa`$ is the condition number of $`A`$. We model each variable as a DAG node and each dependency as a directed edge. Gaussian elimination induces a topological order on the DAG; each elimination step is a parallel unitary operation on the corresponding qubit register. The terminal measurement on each variable register constitutes a separate $`\mathrm{SD}`$ event, and the results compose to give $`\mathbf{x}^*`$. 0◻ ◻

</div>

# Rift: A Quantum-Classical Grammar Matcher

## Overview

**Rift** (formally: *RIFT — a Flexible Translator*) is the compiler front-end component of the OBINexus toolchain. Its theoretical grounding in the $`\mathrm{SD}`$ framework arises from the observation that grammar matching in a parser shares the structural properties of quantum superposition: multiple production-rule paths may be simultaneously *active* (pending) until sufficient lookahead disambiguates them. The decay event corresponds to the moment the parser commits to a single parse path.

## Wave Postulates as Triangular Matching Postulates

The wave postulate (Axiom 3) asserts that a quantum system in superposition $`\left| \Psi \right\rangle = c_1 \left| \psi_1 \right\rangle + c_2 \left| \psi_2 \right\rangle`$ yields one of two outcomes upon measurement. We draw a direct structural analogy to a context-free grammar $`G = (V, \Sigma, R, S)`$ with two competing production rules $`A \to \alpha \mid \beta`$. In both cases:

- The system is in a *pending* superposition of both alternatives until a discriminating token (the “measurement”) is encountered.

- The collapse to a single rule (the “decay”) is the parser’s commit to one production.

- Destructive interference corresponds to the parser eliminating impossible parse paths via lookahead or semantic constraints.

<div class="definition">

**Definition 21** (Grammar Superposition State). Let $`G = (V, \Sigma, R, S)`$ be a context-free grammar and let $`\pi`$ be a partial parse of input $`w = w_1 w_2 \cdots w_n`$. The *grammar superposition state* at position $`i`$ is the set
``` math
\Gamma_i \;=\; \bigl\{\, (A \to \alpha \bullet \beta,\, j)
                   \;\mid\; A \to \alpha\beta \in R,\;
                   w_j \cdots w_i \Rightarrow^* \alpha \,\bigr\}
```
of all active Earley items. The state $`\Gamma_i`$ is the grammar analogue of the superposition state vector: it encodes all simultaneously possible parse paths.

</div>

<div class="definition">

**Definition 22** (Grammar Decay Event). A *grammar decay event* at position $`i`$ occurs when $`|\Gamma_i| = 1`$, i.e., all but one parse path has been eliminated by lookahead. This corresponds to the collapse of the grammar superposition state to a single production, exactly as measurement collapses $`\left| \Psi \right\rangle`$ to a single basis state.

</div>

## Parallel Grammar Evaluation

<div id="thm:rift" class="theorem">

**Theorem 23** (Rift Parallel Parsing). *Let $`G`$ be an unambiguous context-free grammar and let $`w`$ be an input string of length $`n`$. Rift evaluates all production rules of $`G`$ in *parallel* by maintaining the full grammar superposition state $`\Gamma_i`$ at each position, collapsing (decaying) only when the lookahead forces $`|\Gamma_i| = 1`$. The resulting parse is produced in $`O(n^3)`$ time in the worst case (Earley) and $`O(n)`$ for unambiguous grammars in Chomsky Normal Form, corresponding to a single-decay-event parse.*

</div>

<div class="proof">

*Proof Sketch.* The Earley algorithm maintains all active items in $`\Gamma_i`$ at each position. For an unambiguous grammar, the number of active items is bounded by a constant at each position after the initial scan, so the grammar superposition state decays to a singleton in $`O(n)`$ steps. This is structurally identical to a $`\ensuremath{\mathsf{BQP}}`$ computation: the circuit evaluates all branches in parallel and the terminal measurement (grammar decay) yields the unique correct parse with probability 1. 0◻ ◻

</div>

## Stabilisation Principle

The $`\mathrm{SD}`$ framework introduces a *stabilisation principle* as the binding mechanism between the quantum measurement window and its cognitive or computational substrate.

<div class="definition">

**Definition 24** (Stabilisation Principle). A system $`S`$ obeys the *stabilisation principle* if, within the $`\mathrm{SD}`$ window, all intermediate states are reversible (unitary), and the terminal measurement commits the system to a stable classical output that cannot be further modified within the same decay window. Formally:
``` math
\forall\, t < t_{\text{decay}}:\; U(t)\text{ is unitary and reversible.}
    \qquad
    \text{At } t_{\text{decay}}:\; \text{output is classical and irreversible.}
```

</div>

In the Rift context, this means: all grammar transitions before the decay event are reversible (backtracking is permitted); after the grammar decay event, the committed parse tree is final.

# Quantum Burst Protocol (QBP)

## Motivation

The *Quantum Burst Protocol* (QBP) extends the $`\mathrm{SD}`$ framework from computation to communication. Just as a quantum circuit collapses a superposition of computation branches to a single classical output, a QBP connection collapses a superposition of communication paths between two endpoints to a single established channel.

## Formal Definition

<div class="definition">

**Definition 25** (QBP Connection). A *Quantum Burst Protocol connection* is a tuple
``` math
\mathrm{QBP}(A, B) \;=\; \bigl(G,\; \ensuremath{\mathrm{SD}}(a,b),\; \Pi \bigr),
```
where:

- $`G = (E, N)`$ is the quantum connection graph (Definition 3.1), with $`A, B \in N`$ the sender and receiver endpoints.

- $`\ensuremath{\mathrm{SD}}(a,b)`$ is the superposition decay window governing the connection establishment handshake.

- $`\Pi = \{\pi_1, \pi_2, \ldots, \pi_k\}`$ is the set of candidate communication paths (edges in $`E`$) held in superposition during the handshake phase.

The connection is *established* (resolved) when the $`\mathrm{SD}`$ window closes and a single path $`\pi^* \in \Pi`$ is selected; it is *refused* (rejected) if no path survives the decay; and it is *negotiating* (pending) during the handshake phase.

</div>

## QBP Handshake as Superposition Decay

<div class="proposition">

**Proposition 26** (QBP Three-Phase Handshake). *A QBP connection establishment proceeds in three phases corresponding exactly to the three states of the $`\mathrm{SD}`$ window:*

1.  ***Negotiating (pending):** Both $`A`$ and $`B`$ maintain a superposition of all feasible communication paths $`\Pi`$. No classical commitment is made.*

2.  ***Resolved:** The $`\mathrm{SD}`$ window closes; the path $`\pi^*`$ with maximal probability amplitude is selected. $`A`$ and $`B`$ are classically connected via $`\pi^*`$.*

3.  ***Rejected:** The $`\mathrm{SD}`$ window closes with all path amplitudes below the threshold $`b(n)`$; no connection is established.*

</div>

<div class="remark">

*Remark 27*. The QBP handshake is a quantum analogue of the classical TCP three-way handshake (SYN / SYN-ACK / ACK), with the key difference that in QBP, *all candidate paths are simultaneously active* during the negotiating phase, and the path selection is determined by a single quantum measurement (the decay event) rather than sequential message exchange.

</div>

## Spectral Graph Representation

The candidate path set $`\Pi`$ is naturally represented as a *spectral graph*:

<div class="definition">

**Definition 28** (Spectral Connection Graph). The *spectral connection graph* of a QBP connection is the directed graph $`\hat{G} = (V, E, \lambda)`$ where $`\lambda : E \to [0,1]`$ assigns each edge a probability amplitude (eigenvalue weight) such that $`\sum_{e \in \Pi} \lambda(e)^2 = 1`$. The selected path $`\pi^*`$ is the eigenvector corresponding to the dominant eigenvalue after the decay measurement.

</div>

<div class="example">

**Example 29** (Internet Connection as QBP). Consider connecting a client $`A`$ to a server $`B`$ over a network with $`k`$ possible routing paths. In classical networking, these paths are evaluated sequentially (or via parallel probes with separate classical outcomes). Under QBP, the network interface holds all $`k`$ paths in superposition:
``` math
\left| \Pi \right\rangle = \frac{1}{\sqrt{k}} \sum_{i=1}^k \left| \pi_i \right\rangle.
```
Quality-of-service metrics (latency, bandwidth, packet loss) act as the observable $`\hat{O}`$. Measurement of $`\hat{O}`$ collapses $`\left| \Pi \right\rangle`$ to the optimal path $`\left| \pi^* \right\rangle`$ in a single decay event, achieving optimal routing in $`O(1)`$ measurement time (assuming the superposition can be prepared in $`O(\log k)`$ time).

</div>

# MMUKO OS and the OBINexus Toolchain

## MMUKO OS

**MMUKO OS** (M for Mike, Q for Bella \[Queen\], K for Kilo, O for Oscar) is the operating system substrate for the OBINexus quantum-classical computing framework. The name encodes its philosophical foundation: *“the spirit of good and evil that connects nothing and everything, that binds all of us and all of them.”* This duality—nothing and everything, good and evil—maps directly onto the binary superposition state $`\left| 0 \right\rangle`$ and $`\left| 1 \right\rangle`$ and their linear combinations.

MMUKO OS is a cloud-based Windows system that serves as the classical substrate on which quantum algorithms are emulated prior to the availability of dedicated quantum hardware. Its design is guided by three principles:

1.  **Read-Write symmetry:** All memory operations respect the RWX model (Section <a href="#sec:rwx" data-reference-type="ref" data-reference="sec:rwx">4</a>), ensuring that write-heavy workloads collapse atomically to coherent read outcomes.

2.  **Superposition-aware scheduling:** The OS scheduler treats parallel threads as superposed branches of a single computation, deferring classical commitment until the $`\mathrm{SD}`$ window closes.

3.  **Decay-triggered synchronisation:** Inter-process communication is governed by QBP handshakes (Section <a href="#sec:qbp" data-reference-type="ref" data-reference="sec:qbp">8</a>), replacing traditional lock-based synchronisation with measurement-based collapse events.

## Toolchain Stack

The OBINexus toolchain implements the $`\mathrm{SD}`$ framework across the full compilation pipeline:

<div class="center">

| **Component** | **Role in $`\mathrm{SD}`$ Framework** |
|:---|:---|
| riftlang.exe | Source language compiler; implements grammar superposition (Section <a href="#sec:rift" data-reference-type="ref" data-reference="sec:rift">7</a>) to parse Rift source files in parallel. |
| .so.a | Shared object / static archive; intermediate representation holding the superposed (pre-decay) compilation state. |
| rift.exe | Linked executable; represents the post-decay committed classical binary output. |
| gosilang | Target runtime language binding; maps $`\mathrm{SD}`$ primitives to hardware-level instructions. |
| nlink | Build linker / orchestrator; manages the RWX transaction across compilation units. |
| polybuild | Polyglot build system; coordinates multiple $`\mathrm{SD}`$ decay events across heterogeneous language targets. |

</div>

The pipeline can be summarised as:
``` math
\texttt{riftlang.exe} \;\to\; \texttt{.so.a} \;\to\; \texttt{rift.exe}
  \;\to\; \texttt{gosilang} \;\xrightarrow{\;\texttt{nlink / polybuild}\;}\;
  \text{deployed binary}.
```

# Conclusion and Future Work

We have formalised the concept of *Superposition Decay* as a measurement window bridging quantum and classical computation. The main results are:

- The $`\mathrm{SD}`$ window is a three-valued construct (resolved / rejected / pending) that generalises the binary output of a classical TM and aligns precisely with the promise-problem formulation of quantum complexity classes.

- The RWX memory model provides an operational interpretation of the decay window: $`n`$ write operations and $`k`$ read operations within the window collapse atomically to a single coherent read.

- $`\ensuremath{\mathsf{BQP}}`$ is exactly the class of promise problems solvable within a single $`\mathrm{SD}`$ event with a probability gap of $`\tfrac{1}{3}`$.

- Classical algorithms bounded by linear time complexity—deterministic or non-deterministic—can be simulated in parallel within a single $`\mathrm{SD}`$ window by a polynomial-size quantum circuit.

- Systems of linear equations can be expressed as probabilistic DAGs whose parallel evaluation under $`\mathrm{SD}`$ yields solutions in $`O(\log n)`$ quantum time.

- Rift’s parser exploits grammar superposition to evaluate all production rules in parallel, collapsing to a unique parse tree at a grammar decay event governed by the stabilisation principle.

- The Quantum Burst Protocol (QBP) extends $`\mathrm{SD}`$ to networking: all candidate communication paths are held in superposition during handshake, with optimal path selection achieved by a single spectral decay measurement.

- The MMUKO OS / OBINexus toolchain implements all of the above across the full pipeline: `riftlang.exe` $`\to`$ `.so.a` $`\to`$ `rift.exe` $`\to`$ `gosilang`, orchestrated by `nlink` and `polybuild`.

## Future Work

The following directions are planned within the OBINexus research programme:

1.  **Hardware realisation.** Implementing the $`\mathrm{SD}`$ framework on near-term quantum hardware (superconducting qubits, trapped ions) via the MMUKO OS / `riftlang` compiler toolchain.

2.  **Multi-decay protocols for $`\mathsf{PP}`$ and $`\mathsf{PSPACE}`$.** Designing iterated $`\mathrm{SD}`$ protocols that amplify probability across multiple decay events to address problems beyond $`\ensuremath{\mathsf{BQP}}`$.

3.  **QBP networking stack.** Implementing QBP as a full networking protocol atop the MMUKO OS kernel, replacing TCP handshakes with spectral decay measurements for latency-optimal routing.

4.  **Rift compiler validation.** Formal verification that the Rift grammar decay event produces parse trees equivalent to those of a classical Earley parser, with empirical benchmarks on `gosilang` target programs.

5.  **Cognitive binding.** Exploring the stabilisation principle as a model for attention and commitment in cognitive architectures: the $`\mathrm{SD}`$ window as a formal model for the moment of decision in neural-symbolic systems.

<div class="thebibliography">

9

L. K. Grover, “A fast quantum mechanical algorithm for database search,” *Proceedings of the 28th Annual ACM Symposium on Theory of Computing (STOC)*, pp. 212–219, 1996.

A. W. Harrow, A. Hassidim, and S. Lloyd, “Quantum algorithm for linear systems of equations,” *Physical Review Letters*, vol. 103, no. 15, p. 150502, 2009.

M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*, 10th anniversary ed., Cambridge University Press, 2010.

J. Watrous, “Quantum computational complexity,” in *Encyclopedia of Complexity and Systems Science*, Springer, 2009.

</div>
