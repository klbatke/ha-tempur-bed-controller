# Tempur Bed Controller for Home Assistant

> Pilot software. Use only with a controller compatible with the UDP protocol
> implemented by this integration. It is not affiliated with, endorsed by, or
> supported by Tempur-Pedic or any controller manufacturer.

Developed with assistance from ChatGPT (OpenAI Codex).

## What this pilot provides

- UI-based Home Assistant setup for a controller host and UDP port; more than
  one controller can be configured with separate UI names.
- Buttons for lift, flat, memory positions, massage adjustment, massage modes,
  and massage stop.
- Exact 0–10 **requested** intensity controls for head, lumbar, and leg
  massage.
- Last-requested memory-position and massage-mode selections.
- Last-requested head and leg lift actions. These are deliberately not lift
  positions.

## State safety

The observed controller protocol acknowledges commands but does not provide a
validated physical-state query. Consequently, this integration never claims to
know current bed position, current massage intensity, an active preset, or an
active massage mode. Values shown as **requested** or **last requested** mean
only that Home Assistant received an acknowledgement after sending that command.

The lift protocol has only observed Up, Down, and Flat commands—no position
query or measured 0–10 mapping. The pilot therefore cannot honestly expose a
current or estimated lift level.

Changing the bed from a remote, an iPad, or another system can make that
requested state stale. After Home Assistant restarts, requested massage levels
start as unknown. Set an explicit level before using a More or Less button.

## Installation

This repository is not published yet. The audited public release will document
HACS custom-repository installation here.

## Pilot test gate

Do not rely on this integration for safety-critical positioning. Test every
action with clear line of sight to the bed, one action at a time, before adding
automations or voice-assistant exposure.

## Privacy

The public project must not include controller addresses, MAC addresses,
packet-capture files, names of rooms or people, credentials, or network
topology.

## Security

The observed UDP protocol has no validated authentication or encryption. Run
the controller and Home Assistant only on a trusted network, and restrict
network access to the controller according to your own network-security
policy. See [SECURITY.md](SECURITY.md) for the pilot threat model and reporting
guidance.

## License

This project is released under the [MIT License](LICENSE).
