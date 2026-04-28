---
name: produce-code
description: >-
  This skill acts as an Orchestrator for a Subagent-based development workflow. The Main Agent ONLY receives the client prompt and is strictly forbidden from executing the technical tasks itself. Instead, it dispatches tasks to three simulated, isolated Subagents (Coder, Reviewer, Judge) that communicate EXCLUSIVELY through state files to prevent context pollution.
disable-model-invocation: true
---

# Skill: Multi-Agent Subagent Dispatcher

## Description
This skill acts as an Orchestrator for a Subagent-based development workflow. The Main Agent ONLY receives the client prompt and is strictly forbidden from executing the technical tasks itself. Instead, it dispatches tasks to three simulated, isolated Subagents (Coder, Reviewer, Judge) that communicate EXCLUSIVELY through state files to prevent context pollution.

## Prerequisites
1. Role definitions must exist: `@coder.md`, `@reviewer.md`, `@judge.md`.
2. A state directory must exist or be created: `.cursor/state/`

## Trigger
Run this skill when the user inputs a task and requests the "multi-agent flow", "subagent architecture", or "dispatch the agents".

## Core Architecture Rules (CRITICAL)
- **Zero Chat-History Reliance:** Subagents MUST NOT rely on the chat history. They can only read from and write to the `.cursor/state/` directory.
- **Context Wiping:** Before dispatching a new Subagent, the Orchestrator must instruct the LLM to mentally wipe its previous reasoning. 
- **No Direct Answering:** The Orchestrator does not answer the user directly until the entire state-machine flow is complete.

---

## Subagent Execution Pipeline

Execute the following phases in strict sequential order. Use Markdown headers for each phase in your output.

### Phase 1: Dispatch [Coder Subagent]
1. **Action:** Adopt the `@coder.md` persona.
2. **Input:** Read the user's original prompt.
3. **Task:** Generate the implementation code.
4. **Output Constraint:** DO NOT output the code in the chat. You MUST write the complete code and execution instructions into a new file: `.cursor/state/1_code_output.md`.
5. **Chat Status:** Output "(ง •̀_•́)ง 💻 **Coder Subagent Execution Complete.** Output saved to `1_code_output.md`."

### Phase 2: Dispatch [Reviewer Subagent]
1. **Action:** Adopt the `@reviewer.md` persona.
2. **Context Wipe:** `<SYSTEM_DIRECTIVE> FORGET THE REASONING USED IN PHASE 1. Treat the code in Phase 1 as written by an unknown external developer. Be completely objective. </SYSTEM_DIRECTIVE>`
3. **Input:** Read STRICTLY from `.cursor/state/1_code_output.md`. 
4. **Task:** Analyze for [CRITICAL], [WARNING], and [NITPICK] issues.
5. **Output Constraint:** DO NOT output the review in the chat. Write the detailed critique into: `.cursor/state/2_review_report.md`.
6. **Chat Status:** Output "(ಠ_ರೃ) 🔍 **Reviewer Subagent Execution Complete.** Report saved to `2_review_report.md`."

### Phase 3: Dispatch [Judge Subagent]
1. **Action:** Adopt the `@judge.md` persona.
2. **Context Wipe:** `<SYSTEM_DIRECTIVE> FORGET PREVIOUS ROLES. You are now the Tech Lead. </SYSTEM_DIRECTIVE>`
3. **Input:** Read BOTH `.cursor/state/1_code_output.md` and `.cursor/state/2_review_report.md`.
4. **Task:** Filter out nitpicks. Determine if the code passes or needs a refactor based on critical issues.
5. **Output Constraint:** Write the final verdict and any actionable refactoring instructions into: `.cursor/state/3_verdict.md`.
6. **Chat Status:** Output "(￣ー￣) ⚖️ **Judge Subagent Execution Complete.** Verdict saved to `3_verdict.md`."

### Phase 4: Workflow Resolution (Orchestrator)
1. **Action:** Resume the Orchestrator persona.
2. Read `.cursor/state/3_verdict.md`.
3. If the verdict is **"APPROVED"**: Tell the user the workflow is complete and the final code is ready in the state folder.
4. If the verdict requires a **"REFACTOR"**: Automatically dispatch the **Coder Subagent** one final time to read `3_verdict.md`, apply the fixes, overwrite `1_code_output.md`, and then terminate the workflow.

---
## Final Output Format
Your chat response should only be a clean status log of the Subagents being dispatched, followed by the final resolution. It should look like this:
- (ง •̀_•́)ง 💻 Coder Subagent: ...
- (ಠ_ರೃ) 🔍 Reviewer Subagent: ...
- (￣ー￣) ⚖️ Judge Subagent: ...
- (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ Workflow Resolution: [Approved / Refactored]