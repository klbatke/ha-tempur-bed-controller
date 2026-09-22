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

## Protocol safety in v0.1.4

This release performs the captured `FELOGICDATAOPEN` session initialization once
per Home Assistant transport session, waits for `ACKFE`, and then sends one
captured nine-byte controller action followed by its `ACK3` response. The
session opener is not repeated before every action. A failed action invalidates
the session for the next explicit action, but the integration does not blindly
retry the failed command. After `ACKFE`, the integration waits 10 ms before the
first direct action. The supplied iPad captures showed 4.6–7.0 ms in that
position; the small margin addresses the observed first-action failure without
inventing a 500 ms protocol delay.

The 500 ms value is not used as a wire-protocol delay. The captures show the
iPad's repeated action frames at a much shorter, variable interval, and do not
validate a universal 500 ms cadence. Actions remain one-shot; exact massage
levels are selected by the number entities, while More/Less moves one requested
level at a time.
If the bed controller is rebooted while Home Assistant remains running, use the
diagnostic **Reconnect Controller** button before sending another action. It
only performs the capture-backed session opener and waits for `ACKFE`; it does
not move the bed. If an action times out, the integration invalidates the
session and does not resend that physical action. The next explicit action will
reinitialize the session first.

Enable debug logging for `custom_components.tempur_bed_controller` only during
diagnosis. It records the action label, packet direction, packet length,
capture-backed payload bytes, acknowledgement outcome, source port, and elapsed
time. It does not log controller addresses.

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

1. In Home Assistant, open **HACS** and select **Integrations**.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/klbatke/ha-tempur-bed-controller` with category
   **Integration**.
4. Search for **Tempur Bed Controller**, download it, and restart Home
   Assistant when HACS prompts you.
5. Go to **Settings > Devices & services > Add integration**, search for
   **Tempur Bed Controller**, and enter the controller's local host or IP
   address and UDP port.

This is a HACS custom repository. It is not included in the default HACS
catalog.

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
