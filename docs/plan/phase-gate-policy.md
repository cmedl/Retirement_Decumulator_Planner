# Phase Gate Policy

## Purpose

This policy enforces mandatory review and approval before any phase implementation begins.

## Rule

1. No phase may begin until you have formally reviewed that phase plan and explicitly approved it.
2. Approval must be recorded in the Phase Approval Register.
3. If implementation is requested for a phase that is not approved, implementation is blocked and a review request is required first.

## Formal Approval Standard

A phase is considered approved only when both conditions are true:

1. You provide an explicit acceptance message for that phase.
2. The acceptance is recorded in the Phase Approval Register with date and notes.

## Agent Enforcement Behavior

If you request to start a phase and approval is not recorded, I will:

1. Pause implementation.
2. Ask you to review that phase plan.
3. Request explicit approval language.
4. Record approval once you confirm.
5. Continue only after the register is updated.

## Allowed States

1. Pending Review
2. Approved
3. In Progress
4. Complete

## Notes

1. Approval can be revised if requirements change.
2. Any significant scope change returns the phase to Pending Review until re-approved.
