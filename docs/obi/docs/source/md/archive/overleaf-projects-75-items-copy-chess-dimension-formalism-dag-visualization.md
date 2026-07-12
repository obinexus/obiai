---
title: "Chess Dimension Formalism — DAG Visualization"
kind: "archive"
source_archive: "overleaf-projects-75-items-copy"
source_folder: "overleaf-projects-75-items-copy/Chess Dimension Formalism — DAG Visualization"
---

# Chess Dimension Formalism — DAG Visualization

Source folder: `overleaf-projects-75-items-copy/Chess Dimension Formalism — DAG Visualization`

## Extracted Files

- `main.tex`

## main

```latex
% chess_dimensions_dag.tex
\documentclass[12pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{arrows.meta, positioning, shapes.geometric, shadows}
\usepackage{hyperref}
\usepackage{caption}
\usepackage{listings}
\lstset{basicstyle=\ttfamily\small,breaklines=true}
\usepackage{lmodern}

\usepackage{textcomp}
\usepackage{amsfonts}

\title{Chess Dimension Formalism — DAG Visualization}
\author{OBINexus / Draft}
\date{October 2025}

\begin{document}
\maketitle

\begin{abstract}
This document contains a formalised section for the "Chess Dimension" model and a directed acyclic graph (DAG) that visualises the pipeline from board state to per-dimension scoring and final move selection. The DAG is intentionally acyclic to show flow; iterative or cyclical behaviour (search loops, temporal NFA transitions) is handled by external control (search engine, NFA runner).
\end{abstract}

\section{DAG: Dimension Transition Pipeline}
\begin{figure}[ht]
  \centering
  % TikZ DAG
  \begin{tikzpicture}[
      node distance=12mm and 28mm,
      every node/.style={font=\small},
      box/.style={draw, fill=white, rectangle, rounded corners, minimum width=38mm, minimum height=10mm, align=center, drop shadow},
      smallbox/.style={draw, fill=white, rounded corners, minimum width=30mm, minimum height=8mm, align=center},
      arrow/.style={-{Stealth[scale=1]}, line width=0.8pt}
    ]

    % Nodes
    \node[box] (S) {Board State \\ $s\in\mathcal S$};
    \node[box, right=of S] (F) {Feature Extraction \\ $\pi_A,\pi_{Df},\pi_{Of}$};
    \node[smallbox, right=of F, yshift= 10mm] (A) {Attack \\ $u_A(s,m)$};
    \node[smallbox, right=of F, yshift=-10mm] (D) {Defense \\ $u_{Df}(s,m)$};
    \node[smallbox, right=of F, xshift=36mm] (O) {Offense \\ $u_{Of}(s,m)$};
    \node[box, right=of O, xshift=18mm] (M) {Meta-controller \\ combine \& decide \\ $U_{\text{combined}}(m)$};
    \node[box, right=of M] (Move) {Move Selection \\ $m^*=\arg\max U_{\text{combined}}$};
    \node[box, below=of Move, yshift=-6mm] (Next) {Next State \\ $s'=\textsf{apply}(s,m^*)$};

    % Arrows
    \draw[arrow] (S) -- (F) node[midway, above] {extract};
    \draw[arrow] (F) -- (A) node[midway, above, sloped] {attack features};
    \draw[arrow] (F) -- (D) node[midway, above, sloped] {defense features};
    \draw[arrow] (F.east) .. controls +(.9,0) and +(-.9,0) .. (O.west) node[midway, above] {positional features};
    \draw[arrow] (A.east) -- ++(8mm,0) |- (M.north) node[pos=0.85, above] {$U_A(m)$};
    \draw[arrow] (D.east) -- ++(8mm,0) |- (M.south) node[pos=0.9, above] {$U_{Df}(m)$};
    \draw[arrow] (O.east) -- (M.west) node[midway, above] {$U_{Of}(m)$};
    \draw[arrow] (M) -- (Move) node[midway, above] {select};
    \draw[arrow] (Move) -- (Next) node[midway, right] {apply};

    % Styling hints
    \node[below=6mm of F, align=center] (note) {\small Figure: Acyclic pipeline from state to move; repeated play / search loops happen outside this DAG (e.g. repeated application of the pipeline per ply).};
  \end{tikzpicture}
  \caption{Directed Acyclic Graph (DAG) for chess-dimension decision pipeline.}
  \label{fig:chess-dag}
\end{figure}

\section{Accompanying Formal Notes}
The DAG shows a single forward pass for one decision step. In practice:
\begin{itemize}
  \item \textbf{Iterative search.} The Meta-controller may call a search routine (alpha-beta, minimax, MCTS) that iteratively expands the DAG into a search tree/DAG; those internal loops are implemented by the search engine and are not drawn here to keep the figure acyclic.
  \item \textbf{NFA-driven mode switching.} An NFA (observer \(\to\) consumer state machine) can operate in the background to set weights $\omega_A,\omega_{Df},\omega_{Of}$ or to force a single-dimension policy (e.g., urgent defense). The NFA is a control process that does not introduce cycles into this \emph{single-decision} DAG.
  \item \textbf{Coherence \& formation.} Feature extraction computes formation coherence scores $\mathcal C(F)$ and vulnerability metrics used by $u_{Df}$ and $u_{Of}$.
\end{itemize}

\section{LaTeX-ready Pseudocode}
Below is the same selection loop expressed as pseudocode. You can include this in your documentation or use it as a skeleton for implementation.

\begin{lstlisting}[caption={Decision selection pseudocode}]
function SelectMove(s):
    best_m = None
    best_score = -Inf
    for m in LegalMoves(s):
        scoreA = AttackScore(s,m)        # u_A(s,m)
        scoreD = DefenseScore(s,m)       # u_Df(s,m)
        scoreO = OffenseScore(s,m)       # u_Of(s,m)
        combined = wA*scoreA + wD*scoreD + wO*scoreO
        if combined > best_score:
            best_score = combined
            best_m = m
    return best_m
\end{lstlisting}

\section{How to extend the DAG (notes for integration)}
\begin{enumerate}
  \item To visualise iterative search, expand the Move node into a subtree: nodes become states at depth $d$, edges moves, with leaf evaluations fed back into the Meta-controller for minimax aggregation.
  \item To show NFA transitions explicitly, add a parallel ``Controller'' lane above the DAG that outputs $\omega$ weights to the Meta-controller; keep it acyclic by modelling controller decisions as input tokens for a single step.
  \item To show witness logging (HDIS ledger), add a side node that ingests $(s,m^*,\mathcal C,\tau,\sigma)$ for audit; this is an append-only sink and can be drawn as a DAG leaf.
\end{enumerate}
```
