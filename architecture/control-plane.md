# Control-plane architecture

```text
ChatGPT / Codex / OpenCode
            |
            v
  Andromeda Controller
  - task state and history
  - worker registry
  - heartbeat status
  - capability scheduler
  - infrastructure retries
            ^
            | outbound register / heartbeat / poll / result
      +-----+------+----------------+
      |            |                |
  worker1       worker2          worker3
 workstation    hardware lab     cloud simulation
```

The worker always initiates controller traffic. The reference controller does not open inbound connections to workstations.

Software is represented as a versioned capability. Scarce or stateful physical equipment is a resource attached to a worker. Tasks request capability and resource types, never a fixed host identity under normal operation.

## Heartbeat model

- heartbeat every 30 seconds;
- `ONLINE` until 60 seconds without a heartbeat;
- `SUSPECT` from 60 to 120 seconds;
- `OFFLINE` after 120 seconds.

These defaults can be changed on the controller command line. Scheduling uses only `ONLINE` workers.

## Retry model

No compatible online worker is not a failure: the task waits. Loss of a worker during dispatch or execution is an infrastructure failure and is retried up to the task limit. A command failure is terminal in v0.2 so that an engineering owner can diagnose it. Verification failures must be escalated rather than rerun without a changed input or method.
