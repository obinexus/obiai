---
title: "diram boolean logic truth table memory management gates"
kind: "archive"
source_archive: "diram-boolean-logic-truth-table-memory-management-gates"
source_folder: "diram-boolean-logic-truth-table-memory-management-gates"
---

# diram boolean logic truth table memory management gates

Source folder: `diram-boolean-logic-truth-table-memory-management-gates`

## Extracted Files

- `diram_boolean_M1_truth_table.psc.txt`
- `diram_boolean_M2_cache_mechanics.psc.txt`
- `diram_boolean_M3_governance_compliance.psc.txt`
- `diram_boolean_M4_hardware_implementation.psc.txt`
- `diram_boolean_M5_obinexus_integration.psc.txt`

## diram boolean M1 truth table.psc

## diram boolean M1 truth table

// ============================================================
// FILE: diram_boolean_M1_truth_table.psc.txt
// MODULE 1 OF 5 — DIRAM Boolean Logic Truth Table
//                 Input Definitions & Gate Specification
// SOURCE: "DIRAM Boolean Logic Truth Table - Memory Management Gates"
// ORG:    OBINexus Aegis Project | Directed Instruction RAM
// GOVERNANCE: ε(x) ≤ 0.5 | Binary Logic: 2-Input, 1-Output
// ============================================================

// ── CORPUS POSITION ──────────────────────────────────────────
//
// DIRAM (Directed Instruction RAM) is the memory governance layer
// referenced throughout the OBINexus corpus. This document provides
// its formal Boolean logic specification.
//
// Cross-references:
//   PDF 6  (DAG Ephemeris §5.2):
//     DIRAM_validate(transition) = COMMIT if ε(transition) ≤ 0.6
//     → THIS document: ε(x) ≤ 0.5 (DIRAM-specific tighter bound)
//   PDF 7  (OBIAI Thesis):
//     "DIRAM cascade governance constraints"
//   PDF 9  (RAF Cryptographic):
//     entropy_coefficient ≤ 0.5 in QuantumAuraSeal
//     → Matches DIRAM's ε ≤ 0.5 exactly
//   AEGIS-PROOF-3.1/3.2: ε(transition) ≤ 0.6 (higher-level bound)
//
// EPSILON HIERARCHY (resolved):
//   ε ≤ 0.5 — DIRAM hardware-level governance (THIS document)
//   ε ≤ 0.6 — AEGIS/DIRAM integration layer (PDFs 3, 4, 6, 7)
//   The 0.5 bound is STRICTER — hardware enforces tighter compliance
//   before the software 0.6 bound is even reached.

DEFINE DIRAMContext AS:
    full_name       := "Directed Instruction RAM"
    short_name      := "DIRAM"
    governance_eps  := 0.5     // ε(x) ≤ 0.5 — hardware-level constraint
    logic_type      := "2-Input, 1-Output Binary"
    gates_used      := ["NOT", "XOR"]
    output_type     := "Memory Action: 0=Block/Defer, 1=Allow/Process"
END DEFINE


// ── INPUT DEFINITIONS ─────────────────────────────────────────

// INPUT A: Cache State
//   0 = Cache Miss  (data not in cache — must fetch from main memory)
//   1 = Cache Hit   (data present in cache — can serve immediately)

// INPUT B: Governance State
//   0 = ε ≤ 0.5 Compliant   (within safe memory allocation limits)
//   1 = ε > 0.5 Violation   (too many heap events — must throttle)

// OUTPUT: Memory Action
//   0 = Block / Defer   (operation not permitted)
//   1 = Allow / Process (operation permitted)

DEFINE DIRAMInput AS:
    A : {0, 1}    // Cache State: 0=Miss, 1=Hit
    B : {0, 1}    // Governance State: 0=Compliant, 1=Violation
END DEFINE

DEFINE DIRAMOutput AS:
    value : {0, 1}    // Memory Action: 0=Block, 1=Allow
    action : STRING   // human-readable action label
END DEFINE


// ── TRUTH TABLE (CANONICAL) ───────────────────────────────────

//  Input A │ Input B │ NOT A │ A XOR B │ Final Output
//  ────────┼─────────┼───────┼─────────┼─────────────
//    0     │    0    │   1   │    0    │     1      ✅ Allow
//    0     │    1    │   1   │    1    │     0      ❌ Block
//    1     │    0    │   0   │    1    │     1      ✅ Allow
//    1     │    1    │   0   │    0    │     0      ❌ Block

DEFINE DIRAMTruthTable AS:
    rows : List[TruthTableRow]

    ROW_1 := TruthTableRow(A=0, B=0, NOT_A=1, XOR_AB=0, output=1,
                            scenario="Cache Miss + Compliant",
                            decision=ALLOW,
                            explanation="Cache miss with good governance → Fetch data, update cache")

    ROW_2 := TruthTableRow(A=0, B=1, NOT_A=1, XOR_AB=1, output=0,
                            scenario="Cache Miss + Violation",
                            decision=BLOCK,
                            explanation="Cache miss during constraint violation → Defer allocation")

    ROW_3 := TruthTableRow(A=1, B=0, NOT_A=0, XOR_AB=1, output=1,
                            scenario="Cache Hit + Compliant",
                            decision=ALLOW,
                            explanation="Cache hit with good governance → Process immediately")

    ROW_4 := TruthTableRow(A=1, B=1, NOT_A=0, XOR_AB=0, output=0,
                            scenario="Cache Hit + Violation",
                            decision=BLOCK,
                            explanation="Even cache hits blocked during severe violations")
END DEFINE


// ── GATE DEFINITIONS ─────────────────────────────────────────

PROCEDURE NOT_A(A: {0, 1}) -> {0, 1}:
    // Standard logical NOT: inverts cache state
    // A=0 (Miss)  → NOT_A=1 (miss requires action)
    // A=1 (Hit)   → NOT_A=0 (hit needs no extra action)
    RETURN 1 - A
END PROCEDURE


PROCEDURE XOR_AB(A: {0, 1}, B: {0, 1}) -> {0, 1}:
    // Standard logical XOR: detects difference between inputs
    // A=B → XOR=0 (inputs agree — both low or both high)
    // A≠B → XOR=1 (inputs differ — asymmetric state)
    RETURN A XOR B
END PROCEDURE


// ── FINAL OUTPUT LOGIC ────────────────────────────────────────

// The truth table output is computed as:
//   Output = (NOT_A AND NOT XOR_AB) OR (NOT NOT_A AND XOR_AB)
//   Output = (NOT_A AND ¬XOR_AB) OR (A AND XOR_AB)
//
// Equivalently (from C implementation):
//   return (not_a && !xor_ab) || (!not_a && xor_ab)
//
// This is: Output = NOT_A XNOR (A XOR B)... let's verify:
//   Row 1: (1 && !0) || (!1 && 0) = (1&&1)||(0&&0) = 1||0 = 1 ✓
//   Row 2: (1 && !1) || (!1 && 1) = (1&&0)||(0&&1) = 0||0 = 0 ✓
//   Row 3: (0 && !1) || (!0 && 1) = (0&&0)||(1&&1) = 0||1 = 1 ✓
//   Row 4: (0 && !0) || (!0 && 0) = (0&&1)||(1&&0) = 0||0 = 0 ✓

PROCEDURE DIRAMMemoryGate(A: {0, 1}, B: {0, 1}) -> {0, 1}:
    // Core binary gate function: 2-input, 1-output
    not_a   := NOT_A(A)
    xor_ab  := XOR_AB(A, B)

    // Truth table logic: allow when miss+compliant OR hit+compliant
    output := (not_a AND NOT xor_ab) OR (NOT not_a AND xor_ab)
    RETURN output
END PROCEDURE


PROCEDURE LookupTruthTable(A: {0, 1}, B: {0, 1}) -> DIRAMOutput:
    // Direct lookup — faster than gate computation for real-time use
    MATCH (A, B):
        CASE (0, 0): RETURN DIRAMOutput(value=1, action="ALLOW: Fetch data, update cache")
        CASE (0, 1): RETURN DIRAMOutput(value=0, action="BLOCK: Defer allocation")
        CASE (1, 0): RETURN DIRAMOutput(value=1, action="ALLOW: Process immediately")
        CASE (1, 1): RETURN DIRAMOutput(value=0, action="BLOCK: Throttle cache hits")
    END MATCH
END PROCEDURE


PROCEDURE VerifyTruthTableConsistency() -> BOOL:
    // Verify gate computation matches lookup table for all 4 rows.
    all_ok := TRUE
    FOR EACH (A, B) IN [(0,0), (0,1), (1,0), (1,1)]:
        gate_result   := DIRAMMemoryGate(A, B)
        lookup_result := LookupTruthTable(A, B).value
        IF gate_result != lookup_result:
            EMIT ERROR "Inconsistency at (A=" + A + ", B=" + B + "): " +
                       "gate=" + gate_result + " lookup=" + lookup_result
            all_ok := FALSE
        END IF
    END FOR
    IF all_ok:
        EMIT INFO "Truth table consistency verified ✓"
    END IF
    RETURN all_ok
END PROCEDURE


// ============================================================
// END MODULE 1
// NEXT: diram_boolean_M2_cache_mechanics.psc.txt
// ============================================================

## diram boolean M2 cache mechanics.psc

## diram boolean M2 cache mechanics

// ============================================================
// FILE: diram_boolean_M2_cache_mechanics.psc.txt
// MODULE 2 OF 5 — Cache Hit/Miss Mechanics, LRU/MRU Logic
//                 & Lookahead Prediction
// SOURCE: "DIRAM Boolean Logic Truth Table - Memory Management Gates"
// ORG:    OBINexus Aegis Project | Directed Instruction RAM
// ============================================================

// ------------------------------------------------------------
// CACHE HIT / MISS MECHANICS
// ------------------------------------------------------------

// DIRAM uses lookahead memory logic to predict and preload data
// before it is requested. Two outcomes exist when a memory access
// is attempted:


// ── CACHE HIT ────────────────────────────────────────────────

// CACHE HIT (A=1):
//   The requested data is already in cache — no extra fetch needed.
//   System stays fast. Triggers:
//     (a) Memory confirms access
//     (b) State adjustment
//     (c) Nudges related predictions
//     (d) LRU/MRU: promotes item to Most Recently Used position

DEFINE CacheHitRecord AS:
    key          : CacheKey
    value        : CacheValue
    access_time  : Timestamp
    previous_mru_position : INT

    PROCEDURE OnHit(cache: DIRAMCache) -> VOID:
        // (a) Memory confirms access
        EMIT INFO "Cache HIT | key=" + key
        cache.RecordAccess(key, access_time)

        // (b) Update state
        cache.UpdateAccessState(key)

        // (c) Nudge related predictions
        cache.lookahead.NudgePrediction(key, confidence_delta=+0.1)

        // (d) Promote to MRU
        cache.lru_chain.PromoteToMRU(key)
        EMIT LOG "Promoted to MRU: " + key
    END PROCEDURE
END DEFINE


// ── CACHE MISS ───────────────────────────────────────────────

// CACHE MISS (A=0):
//   Data not in cache — system must fetch from main memory or disk.
//   Slower — must wait for fresh data load. Triggers:
//     (a) Lookup fails — no immediate response
//     (b) Fetch from main memory / disk
//     (c) LRU/MRU: must evict Least Recently Used item to make space
//     (d) Load fresh data into cache
//     (e) Update lookahead predictor (miss = prediction failure)

DEFINE CacheMissRecord AS:
    key          : CacheKey
    miss_time    : Timestamp
    fetch_source : {MAIN_MEMORY, DISK}
    evicted_key  : CacheKey OR NULL

    PROCEDURE OnMiss(cache: DIRAMCache,
                      governance_ok: BOOL) -> MissResult:
        EMIT LOG "Cache MISS | key=" + key

        // Check governance before fetching
        IF NOT governance_ok:
            // Row 2 in truth table: A=0, B=1 → BLOCK
            EMIT WARNING "Cache miss blocked by governance violation | key=" + key
            RETURN MissResult(fetched=FALSE, reason="GOVERNANCE_VIOLATION")
        END IF

        // Row 1: A=0, B=0 → ALLOW — fetch and update
        // (c) Evict LRU item if cache full
        evicted := NULL
        IF cache.IsFull():
            evicted := cache.lru_chain.EvictLRU()
            self.evicted_key := evicted
            EMIT INFO "Evicted LRU: " + evicted
        END IF

        // (b) Fetch from main memory or disk
        value := FetchFromSource(key, self.fetch_source)

        // (d) Load into cache
        cache.Insert(key, value)

        // (e) Update lookahead — miss = predictor gap
        cache.lookahead.RecordMiss(key, miss_time)

        RETURN MissResult(fetched=TRUE, evicted=evicted, value=value)
    END PROCEDURE
END DEFINE


// ── LRU/MRU CHAIN ────────────────────────────────────────────

CLASS LRUMRUChain:
    // Doubly-linked list ordered by access recency.
    // Head = Most Recently Used (MRU)
    // Tail = Least Recently Used (LRU)

    PRIVATE:
        chain   : DoublyLinkedList[CacheKey]
        index   : Map[CacheKey → ListNode]

    PUBLIC:

        PROCEDURE PromoteToMRU(key: CacheKey) -> VOID:
            // Move item to head of chain (MRU position)
            IF key IN index:
                node := index[key]
                chain.MoveToHead(node)
                EMIT LOG "LRU/MRU: promoted " + key + " to MRU"
            END IF
        END PROCEDURE

        PROCEDURE EvictLRU() -> CacheKey:
            // Remove and return tail item (Least Recently Used)
            IF chain.IsEmpty():
                EMIT WARNING "LRU chain empty — nothing to evict"
                RETURN NULL
            END IF
            lru_key := chain.Tail().key
            chain.RemoveTail()
            index.REMOVE(lru_key)
            EMIT INFO "LRU evicted: " + lru_key
            RETURN lru_key
        END PROCEDURE

        PROCEDURE Insert(key: CacheKey) -> VOID:
            // Insert new item at MRU position
            node := chain.InsertHead(key)
            index[key] := node
        END PROCEDURE

        PROCEDURE GetMRU() -> CacheKey:
            RETURN chain.Head().key
        END PROCEDURE

        PROCEDURE GetLRU() -> CacheKey:
            RETURN chain.Tail().key
        END PROCEDURE
END CLASS


// ── LOOKAHEAD HARDWARE PREDICTION ────────────────────────────

CLASS DIRAMLookahead:
    // Predicts future cache needs — preloads data it suspects
    // the system will ask for. Raises hit rate over time.
    // Uses confidence scoring aligned with DIRAM's epistemic model
    // (cross-ref: p_conf ≥ 0.954 in AEGIS/OBIAI chain).

    PRIVATE:
        prediction_table : Map[CacheKey → REAL]   // key → confidence ∈ [0,1]
        hit_history      : List[CacheKey]          // recent hits
        miss_history     : List[CacheKey]          // recent misses

    PUBLIC:

        PROCEDURE PredictNextAccess(context: AccessContext) -> List[CacheKey]:
            // Return keys likely to be accessed soon, by confidence rank.
            predictions := SORT_BY(prediction_table,
                                    key=entry → entry.value,
                                    order=DESCENDING)
            CONSTANT PREDICTION_THRESHOLD := 0.5   // matches ε ≤ 0.5 boundary
            RETURN [k FOR (k, conf) IN predictions IF conf >= PREDICTION_THRESHOLD]
        END PROCEDURE

        PROCEDURE NudgePrediction(key: CacheKey, confidence_delta: REAL) -> VOID:
            // Adjust confidence for key based on observed access.
            current := IF key IN prediction_table THEN prediction_table[key] ELSE 0.0
            prediction_table[key] := CLAMP(current + confidence_delta, 0.0, 1.0)
        END PROCEDURE

        PROCEDURE RecordMiss(key: CacheKey, t: Timestamp) -> VOID:
            // Miss = prediction failure — reduce confidence
            miss_history.APPEND(key)
            self.NudgePrediction(key, confidence_delta=-0.05)
        END PROCEDURE

        PROCEDURE PreloadPredicted(cache: DIRAMCache,
                                    governance_ok: BOOL) -> INT:
            // Preload predicted items into cache (if governance permits).
            IF NOT governance_ok:
                EMIT INFO "Lookahead preload skipped — governance violation"
                RETURN 0
            END IF

            predicted := PredictNextAccess(AccessContext.current())
            preloaded := 0
            FOR EACH key IN predicted:
                IF key NOT IN cache.keys:
                    value := FetchFromSource(key, MAIN_MEMORY)
                    cache.Insert(key, value)
                    preloaded := preloaded + 1
                END IF
            END FOR
            EMIT INFO "Lookahead preloaded " + preloaded + " items"
            RETURN preloaded
        END PROCEDURE

END CLASS


// ── DIRAM CACHE STRUCTURE ─────────────────────────────────────

CLASS DIRAMCache:
    PRIVATE:
        store      : Map[CacheKey → CacheValue]
        capacity   : INT
        lru_chain  : LRUMRUChain
        lookahead  : DIRAMLookahead
        sha_receipt_log : List[SHA256Receipt]   // cryptographic traceability

    PUBLIC:

        PROCEDURE Access(key: CacheKey, governance_state: {0, 1}) -> DIRAMOutput:
            // Primary DIRAM access operation.
            // Applies truth table logic: (A=cache_state, B=governance_state)

            A := IF key IN store THEN 1 ELSE 0   // cache state
            B := governance_state

            // Apply DIRAM gate
            decision := LookupTruthTable(A, B)

            IF decision.value == 1:
                IF A == 1:
                    // Cache hit + allowed
                    hit := CacheHitRecord(key=key, access_time=CURRENT_TIME())
                    hit.OnHit(self)
                ELSE:
                    // Cache miss + allowed → fetch
                    miss := CacheMissRecord(key=key, miss_time=CURRENT_TIME())
                    miss.OnMiss(self, governance_ok=TRUE)
                END IF
            ELSE:
                EMIT WARNING "DIRAM BLOCKED | " + decision.action + " | key=" + key
            END IF

            // Generate SHA-256 receipt for traceability
            receipt := GenerateSHAReceipt(key, A, B, decision.value)
            sha_receipt_log.APPEND(receipt)

            RETURN decision
        END PROCEDURE

        PROCEDURE IsFull() -> BOOL:
            RETURN LENGTH(store) >= capacity
        END PROCEDURE

        PROCEDURE Insert(key: CacheKey, value: CacheValue) -> VOID:
            IF IsFull():
                evicted := lru_chain.EvictLRU()
                store.REMOVE(evicted)
            END IF
            store[key] := value
            lru_chain.Insert(key)
        END PROCEDURE

END CLASS


// ── CACHE DECISION FLOW (from document) ──────────────────────

PROCEDURE CacheDecisionFlow(cache: DIRAMCache, key: CacheKey) -> STRING:
    // "Cache Full? → Need Eviction → Check LRU Chain → Remove Oldest"
    // "Cache Hit?  → Promote Item → Move to MRU Position → Update Chain"

    IF key IN cache.store:
        cache.lru_chain.PromoteToMRU(key)
        RETURN "Cache Hit → Promoted to MRU → Chain updated"
    ELSE:
        IF cache.IsFull():
            evicted := cache.lru_chain.EvictLRU()
            RETURN "Cache Full → Eviction → LRU removed: " + evicted
        END IF
        RETURN "Cache Miss → Fetch → Insert at MRU position"
    END IF
END PROCEDURE


// ============================================================
// END MODULE 2
// NEXT: diram_boolean_M3_governance_compliance.psc.txt
// ============================================================

## diram boolean M3 governance compliance.psc

## diram boolean M3 governance compliance

// ============================================================
// FILE: diram_boolean_M3_governance_compliance.psc.txt
// MODULE 3 OF 5 — Sinphase Governance Compliance
//                 ε(x) ≤ 0.5 and SHA-256 Cryptographic Traceability
// SOURCE: "DIRAM Boolean Logic Truth Table - Memory Management Gates"
// ORG:    OBINexus Aegis Project | Directed Instruction RAM
// ============================================================

// ------------------------------------------------------------
// GOVERNANCE CONSTRAINT: ε(x) ≤ 0.5
// ------------------------------------------------------------

// SINPHASE GOVERNANCE MODEL (DIRAM-specific):
//   ε(x) = heap_events / max_events
//
//   ε ≤ 0.5 → B=0 (Compliant)   — within safe limits
//   ε > 0.5 → B=1 (Violation)   — throttle required
//
// EPSILON HIERARCHY NOTE:
//   This document establishes ε ≤ 0.5 as the HARDWARE-LEVEL bound.
//   The ε ≤ 0.6 used in AEGIS/OBIAI integration is the SOFTWARE-LEVEL
//   bound. Hardware enforces the stricter 0.5 constraint first.
//
//   PDF 9  (RAF Cryptographic): entropy_coefficient ≤ 0.5 ← matches
//   PDF 6  (DAG Ephemeris):     ε(transition) ≤ 0.6      ← softer
//   PDFs 3,4 (AEGIS proofs):    ε(x) ≤ 0.6               ← softer
//
//   Resolution: 0.5 (hardware DIRAM) → 0.6 (software AEGIS/OBIAI)
//   Both must hold; hardware gate fires first.

CONSTANT DIRAM_EPSILON_HARDWARE := 0.5    // hardware-level bound (this document)
CONSTANT DIRAM_EPSILON_SOFTWARE  := 0.6   // software-level bound (AEGIS chain)
CONSTANT DIRAM_EPSILON_BOUND     := DIRAM_EPSILON_HARDWARE   // operative bound

DEFINE EpsilonHierarchy AS:
    hardware_bound  := 0.5   // enforced by DIRAM gate (B input to truth table)
    software_bound  := 0.6   // enforced by AEGIS integration layer
    constraint_name := "Sinphase Governance"
    note            := "Hardware checks ε≤0.5 first; if compliant, software checks ε≤0.6"
END DEFINE


// ── SINPHASE COMPLIANCE CHECK (C code formalized) ────────────

// From the document (C implementation):
//   bool diram_check_sinphase_compliance(uint8_t heap_events,
//                                         uint8_t max_events) {
//     double epsilon = (double)heap_events / (double)max_events;
//     return epsilon <= 0.5;  // Updated constraint (not 0.6)
//   }

PROCEDURE DIRAMCheckSinphaseCompliance(heap_events: UINT8,
                                         max_events: UINT8) -> BOOL:
    // Computes ε(x) = heap_events / max_events and checks ≤ 0.5

    IF max_events == 0:
        EMIT ERROR "max_events cannot be zero — undefined ε"
        RETURN FALSE   // conservative: treat as non-compliant
    END IF

    epsilon := heap_events.ToReal() / max_events.ToReal()

    is_compliant := (epsilon <= DIRAM_EPSILON_HARDWARE)

    EMIT LOG "ε(x) = " + heap_events + "/" + max_events +
             " = " + epsilon +
             " | compliant=" + is_compliant

    RETURN is_compliant
END PROCEDURE


PROCEDURE ComputeEpsilon(heap_events: UINT8, max_events: UINT8) -> REAL:
    // ε(x) = heap_events / max_events
    IF max_events == 0:
        RETURN 1.0   // undefined → treat as maximum violation
    END IF
    RETURN heap_events.ToReal() / max_events.ToReal()
END PROCEDURE


// ── GOVERNANCE STATE DERIVATION ──────────────────────────────

PROCEDURE DeriveGovernanceState(heap_events: UINT8,
                                  max_events: UINT8) -> {0, 1}:
    // Maps compliance to DIRAM input B:
    //   B=0: ε ≤ 0.5 → Compliant → system within safe limits
    //   B=1: ε > 0.5 → Violation → too many heap events

    IF DIRAMCheckSinphaseCompliance(heap_events, max_events):
        RETURN 0   // Compliant
    ELSE:
        RETURN 1   // Violation
    END IF
END PROCEDURE


// ── GOVERNANCE STATE DESCRIPTIONS ────────────────────────────

DEFINE GovernanceStateSpec AS:
    STATE_0 := {
        value       : 0,
        condition   : "ε ≤ 0.5",
        meaning     : "System running within safe memory allocation limits",
        description : "Heap event rate does not exceed 50% of maximum",
        diram_action: "Allow cache operations (subject to cache state A)"
    }

    STATE_1 := {
        value       : 1,
        condition   : "ε > 0.5",
        meaning     : "Too many heap events — system must throttle allocations",
        description : "Heap event rate exceeds 50% of maximum capacity",
        diram_action: "Block ALL operations regardless of cache state A"
    }

    // Note on Row 4 (A=1, B=1):
    //   Even a Cache HIT is blocked when governance violation is active.
    //   This ensures governance compliance takes absolute priority —
    //   the system cannot be lured into unsafe operation by cache availability.
END DEFINE


// ── HEAP EVENT TRACKING ───────────────────────────────────────

CLASS HeapEventTracker:
    PRIVATE:
        event_count : UINT8
        max_events  : UINT8
        event_log   : List[HeapEvent]

    PUBLIC:

        PROCEDURE Initialize(max_events: UINT8) -> VOID:
            self.max_events  := max_events
            self.event_count := 0
            self.event_log   := []
        END PROCEDURE

        PROCEDURE RecordEvent(event: HeapEvent) -> BOOL:
            // Record a heap event. Returns FALSE if recording this event
            // would push ε above 0.5 (pre-emptive throttle).
            IF event_count >= max_events:
                EMIT ERROR "Heap event count at maximum — rejecting new event"
                RETURN FALSE
            END IF

            new_count := event_count + 1
            new_eps   := new_count.ToReal() / max_events.ToReal()

            IF new_eps > DIRAM_EPSILON_HARDWARE:
                EMIT WARNING "Recording this event would push ε=" + new_eps +
                             " > 0.5 — event logged but governance flag set"
                // Still log for audit, but flag violation
                event.violation := TRUE
            END IF

            event_count := new_count
            event_log.APPEND(event)
            RETURN TRUE
        END PROCEDURE

        PROCEDURE CurrentEpsilon() -> REAL:
            RETURN ComputeEpsilon(event_count, max_events)
        END PROCEDURE

        PROCEDURE IsCompliant() -> BOOL:
            RETURN CurrentEpsilon() <= DIRAM_EPSILON_HARDWARE
        END PROCEDURE

        PROCEDURE Reset() -> VOID:
            event_count := 0
            event_log   := []
            EMIT INFO "Heap event tracker reset"
        END PROCEDURE

        PROCEDURE GetGovernanceState() -> {0, 1}:
            RETURN IF IsCompliant() THEN 0 ELSE 1
        END PROCEDURE

END CLASS


// ── SHA-256 CRYPTOGRAPHIC TRACEABILITY ────────────────────────

// From the document:
//   "SHA-256 receipts generated for every cache operation"
//   "Cryptographic traceability for security"
//
// Cross-reference:
//   PDF 9 (RAF Cryptographic): AuraSeal uses cryptographic signatures
//   PDF 5 (Hospital Safety):   GenerateAuditTrail per medical standard
//   DIRAM: SHA-256 at the hardware cache operation level

DEFINE SHA256Receipt AS:
    operation_id   : UUID
    cache_key      : CacheKey
    cache_state_A  : {0, 1}
    governance_B   : {0, 1}
    not_a_gate     : {0, 1}
    xor_ab_gate    : {0, 1}
    output         : {0, 1}
    epsilon_value  : REAL
    timestamp      : Timestamp
    hash           : BYTES[32]    // SHA-256 digest

    INVARIANT: hash == SHA256(SerializeReceipt(self))
END DEFINE


PROCEDURE GenerateSHAReceipt(key: CacheKey,
                               A: {0, 1}, B: {0, 1},
                               output: {0, 1}) -> SHA256Receipt:
    // Generate SHA-256 audit receipt for a single cache gate operation.
    not_a  := NOT_A(A)
    xor_ab := XOR_AB(A, B)

    receipt := SHA256Receipt(
        operation_id  = GenerateUUID(),
        cache_key     = key,
        cache_state_A = A,
        governance_B  = B,
        not_a_gate    = not_a,
        xor_ab_gate   = xor_ab,
        output        = output,
        epsilon_value = 0.0,    // filled by caller if available
        timestamp     = CURRENT_TIMESTAMP(),
        hash          = ZERO_BYTES(32)   // placeholder before hashing
    )

    // Compute SHA-256 hash of all fields except hash itself
    payload      := SerializeReceipt(receipt)
    receipt.hash := SHA256(payload)

    EMIT LOG "SHA-256 receipt: " + receipt.hash.ToHex()[:16] + "..."
    RETURN receipt
END PROCEDURE


PROCEDURE VerifySHAReceipt(receipt: SHA256Receipt) -> BOOL:
    // Verify cryptographic integrity of a stored receipt.
    expected_hash := SHA256(SerializeReceiptWithoutHash(receipt))
    RETURN receipt.hash == expected_hash
END PROCEDURE


PROCEDURE AuditReceiptLog(log: List[SHA256Receipt]) -> AuditResult:
    // Verify all receipts in log are cryptographically intact.
    n_total  := LENGTH(log)
    n_valid  := 0
    failures := []

    FOR EACH receipt IN log:
        IF VerifySHAReceipt(receipt):
            n_valid := n_valid + 1
        ELSE:
            failures.APPEND(receipt.operation_id)
            EMIT WARNING "Receipt integrity failure: " + receipt.operation_id
        END IF
    END FOR

    RETURN AuditResult(
        n_total      = n_total,
        n_valid      = n_valid,
        n_failures   = LENGTH(failures),
        failed_ids   = failures,
        integrity_ok = (LENGTH(failures) == 0)
    )
END PROCEDURE


// ============================================================
// END MODULE 3
// NEXT: diram_boolean_M4_hardware_implementation.psc.txt
// ============================================================

## diram boolean M4 hardware implementation.psc

## diram boolean M4 hardware implementation

// ============================================================
// FILE: diram_boolean_M4_hardware_implementation.psc.txt
// MODULE 4 OF 5 — Hardware Implementation:
//                 C Gate Code, Address Layout & Memory Evolution
// SOURCE: "DIRAM Boolean Logic Truth Table - Memory Management Gates"
// ORG:    OBINexus Aegis Project | Directed Instruction RAM
// ============================================================

// ------------------------------------------------------------
// HARDWARE IMPLEMENTATION
// ------------------------------------------------------------

// DIRAM extends traditional RAM from PASSIVE to ACTIVE memory:
//   Traditional RAM: responds to requests (passive)
//   DIRAM:           makes intelligent decisions (active) using:
//     (a) Binary logic gates for fast decision-making
//     (b) Cache hit/miss prediction patterns
//     (c) Governance constraints preventing resource exhaustion
//     (d) Cryptographic traceability for security


// ── C GATE CODE FORMALIZED ────────────────────────────────────

// From the document (C implementation, decoded from obfuscated text):
//
//   #include "diram"
//
//   // Binary decision function
//   uint8_t diram_memory_gate(uint8_t cache_state,
//                              uint8_t governance_state) {
//     uint8_t not_a   = !cache_state;
//     uint8_t xor_ab  = cache_state ^ governance_state;
//
//     // Truth table logic: various combinations based on requirements
//     return (not_a && !xor_ab) || (!not_a && xor_ab);
//   }

PROCEDURE DIRAMMemoryGate_C_Formalized(cache_state: UINT8,
                                         governance_state: UINT8) -> UINT8:
    // Direct pseudocode translation of the C implementation.
    // Operates on 8-bit unsigned integers (binary: 0 or 1).

    // Validate inputs are binary
    ASSERT cache_state IN [0, 1]
    ASSERT governance_state IN [0, 1]

    // Gate computations
    not_a  := (NOT cache_state) AND 0x01    // uint8_t !cache_state
    xor_ab := cache_state XOR governance_state  // uint8_t xor

    // Truth table output:
    //   (not_a && !xor_ab) || (!not_a && xor_ab)
    term_1 := not_a AND (NOT xor_ab AND 0x01)
    term_2 := (NOT not_a AND 0x01) AND xor_ab
    result := term_1 OR term_2

    RETURN result AND 0x01    // ensure single-bit output
END PROCEDURE


// Compliance check (C code formalized):
//   bool diram_check_sinphase_compliance(uint8_t heap_events,
//                                         uint8_t max_events) {
//     double epsilon = (double)heap_events / (double)max_events;
//     return epsilon <= 0.5;
//   }
//   (See Module 3 for full implementation)


// ── HARDWARE ADDRESS LAYOUT ───────────────────────────────────

// The gates act as CHECKPOINTS — binary decisions on whether
// information should be stored, passed through, or flipped.
//
// Hardware can see cache layout patterns:
//   - Address tracing
//   - LRU/MRU transitions (binary decisions based on access patterns)
//   - Predictive allocation using historical patterns
//   - Governance enforcement at hardware level

DEFINE DIRAMMemoryLayout AS:
    // Hardware memory address structure for DIRAM cache
    address_width   : INT        // bits per address (e.g., 64)
    cache_lines     : INT        // number of cache lines
    line_size_bytes : INT        // bytes per cache line

    // Address breakdown:
    //   [tag bits | set index bits | block offset bits]
    tag_bits        : INT
    set_index_bits  : INT
    offset_bits     : INT

    // Governance metadata per address region:
    epsilon_register  : REAL     // current ε for this memory region
    lru_chain_pointer : Address  // pointer to LRU chain head for this set
    sha_log_pointer   : Address  // pointer to SHA receipt log
END DEFINE


PROCEDURE ComputeAddressComponents(address: UINT64,
                                    layout: DIRAMMemoryLayout) -> AddressComponents:
    // Decompose a memory address into its tag/set/offset components.

    offset_mask    := (1 << layout.offset_bits)    - 1
    set_mask       := (1 << layout.set_index_bits) - 1
    tag_mask       := (1 << layout.tag_bits)       - 1

    block_offset   := address AND offset_mask
    set_index      := (address >> layout.offset_bits) AND set_mask
    tag            := (address >> (layout.offset_bits + layout.set_index_bits)) AND tag_mask

    RETURN AddressComponents(tag=tag, set=set_index, offset=block_offset)
END PROCEDURE


// ── CACHE HIT PATTERN ANALYSIS ────────────────────────────────

// From document:
//   "Cache hit often aligns with predictable output patterns (like repeated 1s)"
//   "Cache miss comes from unpredictable or rare signal paths — where XOR
//    flips unexpectedly or NOT cancels out expected inputs"

PROCEDURE AnalyzeAccessPattern(access_history: List[{A: {0,1}, B: {0,1}}]) -> PatternReport:
    // Identify predictable vs. unpredictable access patterns.

    n := LENGTH(access_history)
    IF n == 0:
        RETURN PatternReport(predictable=0, unpredictable=0)
    END IF

    hit_sequence     := [1 FOR (A, B) IN access_history IF A == 1]
    miss_sequence    := [0 FOR (A, B) IN access_history IF A == 0]
    xor_flips        := [XOR_AB(A, B) FOR (A, B) IN access_history]
    not_cancellations := [1 FOR (A, B) IN access_history IF NOT_A(A) == 0 AND XOR_AB(A,B) == 0]

    // Predictable: hits with low XOR activity
    n_hits         := LENGTH(hit_sequence)
    n_xor_flips    := SUM(xor_flips)
    n_not_cancels  := LENGTH(not_cancellations)

    hit_rate       := n_hits / n
    xor_flip_rate  := n_xor_flips / n

    predictability := hit_rate * (1.0 - xor_flip_rate)

    EMIT INFO "Access pattern | hit_rate=" + hit_rate +
              " | xor_flip_rate=" + xor_flip_rate +
              " | predictability=" + predictability

    RETURN PatternReport(
        n_total        = n,
        hit_rate       = hit_rate,
        xor_flip_rate  = xor_flip_rate,
        predictability = predictability,
        n_not_cancels  = n_not_cancels,
        predictable    = FLOOR(predictability * n),
        unpredictable  = n - FLOOR(predictability * n)
    )
END PROCEDURE


// ── MEMORY EVOLUTION: RANDOM → DIRECTED ──────────────────────

// Traditional RAM vs. DIRAM comparison (from §"Memory Evolution"):

DEFINE MemoryEvolution AS:

    TRADITIONAL_RAM := {
        model       : "Passive storage responding to requests",
        decision    : "None — always serve if addressed",
        governance  : "None",
        traceability: "None",
        prediction  : "None"
    }

    DIRAM := {
        model       : "Active memory making intelligent decisions",
        decision    : "Binary logic gates (NOT, XOR) → truth table",
        governance  : "ε(x) ≤ 0.5 Sinphase constraint enforced at hardware",
        traceability: "SHA-256 receipts for every cache operation",
        prediction  : "Lookahead confidence scoring preloads likely data"
    }

    EVOLUTION_QUOTE := "Memory that doesn't just store—it thinks, predicts, and " +
                       "governs its own allocation patterns using boolean logic."
END DEFINE


PROCEDURE CompareModels(address: UINT64, request: MemoryRequest) -> ComparisonResult:
    // Demonstrate Traditional RAM vs DIRAM decision for same request.

    // Traditional RAM: always serves
    trad_result := MemoryResult(
        served = TRUE,
        decision = "ALWAYS_SERVE",
        governance_checked = FALSE,
        receipt = NULL
    )

    // DIRAM: gate-checked
    heap_tracker  := HeapEventTracker.current()
    A             := IF CacheContains(address) THEN 1 ELSE 0
    B             := heap_tracker.GetGovernanceState()

    diram_output  := LookupTruthTable(A, B)
    receipt       := GenerateSHAReceipt(address.ToKey(), A, B, diram_output.value)

    diram_result := MemoryResult(
        served             = (diram_output.value == 1),
        decision           = diram_output.action,
        governance_checked = TRUE,
        receipt            = receipt
    )

    RETURN ComparisonResult(
        traditional = trad_result,
        diram       = diram_result,
        diverges    = (trad_result.served != diram_result.served)
    )
END PROCEDURE


// ── PREDICTIVE ALLOCATION ─────────────────────────────────────

// "Uses historical patterns to forecast future needs"
// Confidence scoring aligns with the OBIAI epistemic framework:
//   p_conf ≥ 0.954 → FILTER mode (persistent, deliberate)
//   Applied here: prediction_confidence ≥ 0.5 → preload (matches ε ≤ 0.5)

PROCEDURE PredictiveAllocationCycle(cache: DIRAMCache,
                                     heap_tracker: HeapEventTracker,
                                     pattern_report: PatternReport) -> AllocationPlan:
    // Plan allocation for next cycle based on observed patterns.

    governance_ok := heap_tracker.IsCompliant()

    IF NOT governance_ok:
        EMIT INFO "Predictive allocation skipped — governance violation"
        RETURN AllocationPlan(preloads=[], reason="GOVERNANCE_BLOCKED")
    END IF

    // Use pattern predictability to decide preload depth
    IF pattern_report.predictability >= 0.7:
        preload_count := 4    // high predictability → preload more
    ELSE IF pattern_report.predictability >= 0.5:
        preload_count := 2    // medium predictability
    ELSE:
        preload_count := 0    // unpredictable → don't waste bandwidth
    END IF

    predicted_keys := cache.lookahead.PredictNextAccess(AccessContext.current())
    keys_to_load   := predicted_keys[:preload_count]

    EMIT INFO "Predictive allocation | count=" + preload_count +
              " | keys=" + keys_to_load
    RETURN AllocationPlan(preloads=keys_to_load, reason="PREDICTED")
END PROCEDURE


// ============================================================
// END MODULE 4
// NEXT: diram_boolean_M5_obinexus_integration.psc.txt
// ============================================================

## diram boolean M5 obinexus integration.psc

## diram boolean M5 obinexus integration

// ============================================================
// FILE: diram_boolean_M5_obinexus_integration.psc.txt
// MODULE 5 OF 5 — OBINexus Corpus Integration & Final Index
// SOURCE: "DIRAM Boolean Logic Truth Table - Memory Management Gates"
// ORG:    OBINexus Aegis Project | Directed Instruction RAM
// ============================================================

// ------------------------------------------------------------
// DIRAM AS THE HARDWARE SUBSTRATE OF THE OBIAI STACK
// ------------------------------------------------------------

// DIRAM is referenced throughout the corpus but never fully
// specified at the binary gate level until this document.
// This module maps DIRAM's truth table behavior to every
// higher-level abstraction that depends on it.


// ── DIRAM GATE IN THE AEGIS PROOF CHAIN ──────────────────────

DEFINE DIRAMCorpusConnections AS:

    // PDF 3 (AEGIS-PROOF-1.2): EpistemicDAG traversal uses DIRAM commit/rollback
    CONNECT_PDF3 := {
        higher_abstraction : "DIRAM_validate(transition) = COMMIT/ROLLBACK",
        hardware_substrate : "DIRAMMemoryGate(A, B) → Allow/Block",
        mapping            : "COMMIT ↔ output=1 (ALLOW); ROLLBACK ↔ output=0 (BLOCK)",
        epsilon_note       : "PDF 3 uses ε≤0.6; DIRAM gate uses ε≤0.5 below that"
    }

    // PDF 4 (AEGIS-PROOF-3.2): Hybrid convergence writes to DIRAM-governed memory
    CONNECT_PDF4 := {
        higher_abstraction : "J(vₙ,nₙ) → J* stored in DIRAM-governed memory",
        hardware_substrate : "Each parameter update is a cache write gate operation",
        mapping            : "Convergence requires B=0 (compliant) for writes to persist",
        epsilon_note       : "Robbins-Monro noise ξₙ must not push ε > 0.5"
    }

    // PDF 6 (DAG Ephemeris): DIRAM governs verb-noun capsule persistence
    CONNECT_PDF6 := {
        higher_abstraction : "DIRAM_validate(transition): COMMIT if ε≤0.6",
        hardware_substrate : "DIRAMMemoryGate(A=capsule_cached, B=governance_state)",
        mapping            : "Flash capsule persists only when gate outputs ALLOW",
        epsilon_note       : "Hardware ε≤0.5 is prerequisite for software ε≤0.6 commit"
    }

    // PDF 7 (OBIAI): DIRAM cascade persona management
    CONNECT_PDF7 := {
        higher_abstraction : "DIRAM cascade model: Obinexus→Uche→Eze activation",
        hardware_substrate : "Each cascade tier activation is a DIRAM gate decision",
        mapping            : "Tier activates only when gate ALLOWS (output=1)",
        epsilon_note       : "Cascade uses drift-based ε; hardware floor is 0.5"
    }

    // PDF 9 (RAF): QuantumAuraSeal uses entropy_coefficient ≤ 0.5
    CONNECT_PDF9 := {
        higher_abstraction : "entropy_coefficient ≤ 0.5 in QuantumAuraSeal",
        hardware_substrate : "DIRAMCheckSinphaseCompliance(heap_events, max_events)",
        mapping            : "IDENTICAL bound: both use 0.5 as the operative threshold",
        epsilon_note       : "RAF 0.5 and DIRAM 0.5 are the same underlying constraint"
    }

    // PDF 11 (DGT Variadic): D_act computability bound maps to memory allocation
    CONNECT_PDF11 := {
        higher_abstraction : "Θ = 8 active dimensions (computability bound)",
        hardware_substrate : "DIRAM cache capacity = analogue of Θ in memory domain",
        mapping            : "When |D_act| > Θ, evict LRU dimension (same logic as cache eviction)",
        epsilon_note       : "Dimension activation governed by ε; full cache = governance risk"
    }
END DEFINE


// ── FULL DIRAM INTEGRATION PROCEDURE ─────────────────────────

PROCEDURE RunDIRAMIntegratedOperation(
    cache_key     : CacheKey,
    heap_events   : UINT8,
    max_events    : UINT8,
    cache         : DIRAMCache) -> IntegratedResult:

    // Step 1: Compute governance state (B) from Sinphase check
    B := DeriveGovernanceState(heap_events, max_events)
    epsilon := ComputeEpsilon(heap_events, max_events)

    // Step 2: Determine cache state (A)
    A := IF cache_key IN cache.store THEN 1 ELSE 0

    // Step 3: Apply DIRAM gate
    output := DIRAMMemoryGate(A, B)

    // Step 4: Execute based on output
    cache_result := cache.Access(cache_key, governance_state=B)

    // Step 5: Generate SHA-256 receipt
    receipt := GenerateSHAReceipt(cache_key, A, B, output)
    receipt.epsilon_value := epsilon

    // Step 6: Classify outcome
    zone := ClassifyEpsilonZone(epsilon)

    RETURN IntegratedResult(
        A=A, B=B, output=output,
        action=cache_result.action,
        epsilon=epsilon,
        zone=zone,
        receipt=receipt
    )
END PROCEDURE


PROCEDURE ClassifyEpsilonZone(epsilon: REAL) -> STRING:
    // Map ε to operational zone (bridges DIRAM to OBIAI failure scale)
    IF epsilon <= 0.25:   RETURN "SAFE"          // well within bounds
    IF epsilon <= 0.50:   RETURN "NOMINAL"        // at DIRAM hardware limit
    IF epsilon <= 0.60:   RETURN "SOFT_WARNING"   // AEGIS software layer active
    IF epsilon <= 0.75:   RETURN "HARD_WARNING"   // approaching crisis
    RETURN "VIOLATION"                            // full governance breach
END PROCEDURE


// ── TRUTH TABLE AS ROUTING LOGIC IN OBIAI ────────────────────

// The 4 truth table rows map to 4 operational states in OBIAI:

DEFINE OBIAIStateMapping AS:

    ROW1_ALLOW_MISS := {
        diram       : "(A=0, B=0) → output=1",
        obiai_state : "FLASH → FILTER elevation candidate",
        meaning     : "Cache miss + compliant → attempt to persist Flash result",
        action      : "FilterLayer.Integrate(flash_result) if CanPersist()",
        file_ref    : "obiai_thesis_M3_implementation_modules.psc.txt"
    }

    ROW2_BLOCK_MISS := {
        diram       : "(A=0, B=1) → output=0",
        obiai_state : "FLASH blocked — governance violation during miss",
        meaning     : "New data cannot be loaded — system must wait for ε to drop",
        action      : "Return Flash result without cache persistence",
        file_ref    : "obiai_thesis_M3_implementation_modules.psc.txt"
    }

    ROW3_ALLOW_HIT := {
        diram       : "(A=1, B=0) → output=1",
        obiai_state : "FILTER mode — persistent data available and compliant",
        meaning     : "Ideal operating state — high confidence, low overhead",
        action      : "FilterLayer.Process(cached_data) immediately",
        file_ref    : "aegis_proof_3_1_3_2_M5_compliance_algorithm.psc.txt"
    }

    ROW4_BLOCK_HIT := {
        diram       : "(A=1, B=1) → output=0",
        obiai_state : "ALL modes blocked — governance violation overrides cache",
        meaning     : "Even available Filter data cannot be served safely",
        action      : "TriggerEmergencyStop() or DIRAMCascade.ActivateTier(EZE)",
        file_ref    : "obiai_thesis_M2_diram_cascade_algorithm.psc.txt"
    }
END DEFINE


// ── EPSILON HIERARCHY RESOLUTION (COMPLETE) ──────────────────

PROCEDURE ResolveEpsilonBound(context: OperationalContext) -> REAL:
    // Determine which ε bound applies at this context level.

    MATCH context.level:
        CASE HARDWARE_DIRAM:
            RETURN 0.5    // THIS DOCUMENT — strictest hardware gate
        CASE SOFTWARE_RAF_QUANTUM:
            RETURN 0.5    // PDF 9 RAF — matches hardware level
        CASE SOFTWARE_AEGIS_OBIAI:
            RETURN 0.6    // PDFs 3,4,6,7 — software integration layer
        CASE SINPHASE_GOVERNANCE:
            RETURN 0.6    // PDF 2 Actor Class — architectural constant
    END MATCH

    RETURN 0.5   // conservative default — use hardware bound
END PROCEDURE


// ── COMPLETE CORPUS INDEX (12 PDFs, 60 Modules) ──────────────

PROCEDURE PrintFinalCorpusIndex() -> VOID:
    EMIT INFO "=========================================================="
    EMIT INFO "COMPLETE OBINEXUS PSEUDOCODE CORPUS — FINAL"
    EMIT INFO "12 PDFs → 60 Modules | Nnamdi Michael Okpala, OBINexus"
    EMIT INFO "Span: May 2025 – May 2026"
    EMIT INFO "=========================================================="
    EMIT INFO ""
    EMIT INFO "── AEGIS PROOF CHAIN ──────────────────────────────────────"
    EMIT INFO "PDF 1  Bayesian Debiasing (July 4, 2025)"
    EMIT INFO "       bayesian_debiasing_M1–M5.psc.txt"
    EMIT INFO "PDF 2  Actor Class (2025)"
    EMIT INFO "       actor_class_M1–M5.psc.txt"
    EMIT INFO "PDF 3  AEGIS-PROOF-1.2 Traversal Cost (May 27, 2025)"
    EMIT INFO "       aegis_proof_1_2_M1–M5.psc.txt"
    EMIT INFO "PDF 4  AEGIS-PROOF-3.1 & 3.2 (August 2025)"
    EMIT INFO "       aegis_proof_3_1_3_2_M1–M5.psc.txt"
    EMIT INFO "PDF 5  AEGIS-PROOF-4.1 Hospital Safety (August 2025)"
    EMIT INFO "       aegis_proof_4_1_M1–M5.psc.txt"
    EMIT INFO "PDF 6  DAG Ephemeris Spec (August 2025)"
    EMIT INFO "       dag_ephemeris_M1–M5.psc.txt"
    EMIT INFO "PDF 7  OBIAI Thesis (September 2025)"
    EMIT INFO "       obiai_thesis_M1–M5.psc.txt"
    EMIT INFO ""
    EMIT INFO "── DIMENSIONAL GAME THEORY SUB-SERIES ────────────────────"
    EMIT INFO "PDF 8  DGT Formal: Nash/Theorem 1 (July 4, 2025)"
    EMIT INFO "       dimensional_game_theory_M1–M5.psc.txt"
    EMIT INFO "PDF 9  DGT-RAF Cryptographic (August 2025)"
    EMIT INFO "       raf_cryptographic_M1–M5.psc.txt"
    EMIT INFO "PDF 10 DGT Variadic V2 Reissue (May 24, 2026)"
    EMIT INFO "       dgt_variadic_M1–M5.psc.txt"
    EMIT INFO "PDF 11 DGT Variadic V1 ORIGINAL (July 4, 2025)"
    EMIT INFO "       dgt_variadic_v1_M1–M5.psc.txt"
    EMIT INFO ""
    EMIT INFO "── DIRAM HARDWARE LAYER ───────────────────────────────────"
    EMIT INFO "PDF 12 DIRAM Boolean Logic Truth Table  ← THIS"
    EMIT INFO "       diram_boolean_M1_truth_table.psc.txt"
    EMIT INFO "       diram_boolean_M2_cache_mechanics.psc.txt"
    EMIT INFO "       diram_boolean_M3_governance_compliance.psc.txt"
    EMIT INFO "       diram_boolean_M4_hardware_implementation.psc.txt"
    EMIT INFO "       diram_boolean_M5_obinexus_integration.psc.txt  ← THIS"
    EMIT INFO ""
    EMIT INFO "=========================================================="
    EMIT INFO "GLOBAL INVARIANTS (all 12 documents):"
    EMIT INFO "  EPISTEMIC_THRESHOLD         := 0.954"
    EMIT INFO "  DIRAM_EPSILON_HARDWARE      := 0.5  ← PDF 12 (strictest)"
    EMIT INFO "  DIRAM_EPSILON_RAF_QUANTUM   := 0.5  ← PDF 9"
    EMIT INFO "  DIRAM_EPSILON_SOFTWARE      := 0.6  ← PDFs 3,4,6,7"
    EMIT INFO "  SINPHASE_BOUND              := 0.6  ← PDFs 2,3,4,5"
    EMIT INFO "  THETA_COMPUTABILITY         := 8"
    EMIT INFO "  STRESS_RANGE                := [0, 12]"
    EMIT INFO "  TRIPOLAR                    := {UCHE, EZE, OBI}"
    EMIT INFO "  SHA256_RECEIPT_PER_OP       := TRUE  ← PDF 12 (DIRAM)"
    EMIT INFO ""
    EMIT INFO "FOUNDING DAY (July 4, 2025): PDFs 1, 8, 11"
    EMIT INFO "HARDWARE FOUNDATION:          PDF 12 (DIRAM Boolean Logic)"
    EMIT INFO "=========================================================="
END PROCEDURE


// ============================================================
// END MODULE 5 — CORPUS COMPLETE
//
// TOTAL: 12 PDFs → 60 MODULES
// DIRAM provides the hardware gate substrate for the entire
// OBINexus OBIAI/AEGIS stack.
// ============================================================
