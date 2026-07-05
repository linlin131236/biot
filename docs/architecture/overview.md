# Architecture Notes

Bolt is split into a desktop shell and an agent core.

- The desktop shell owns user interaction, permission prompts, diff review, and local app UX.
- The agent core owns context packets, tool requests, risk classification, failure memory, and model routing.
- Tools must not bypass permission gates.
- Agent decisions receive a compact P0 context, not the full world model.
