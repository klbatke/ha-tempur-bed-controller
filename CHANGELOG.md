# Changelog

## 0.1.7

- Send one acknowledged **Massage Stop** at integration startup to establish
  the requested level-zero baseline before enabling massage controls.
- Keep massage controls unavailable when Stop is unconfirmed instead of
  presenting an actionable unknown intensity.
- Add a transparent **Massage Safety State** sensor.
- Reset a 30-minute safety timer after acknowledged HA-issued active massage;
  expiry sends one serialized Massage Stop.
- Keep Stop one-shot after a missing `ACK3`; the integration never claims a
  stopped state without acknowledgement.

## 0.1.5

- Reopen the capture-backed controller session before the next explicit action
  after 120 seconds of controller inactivity. The opener must receive `ACKFE`
  before the requested action is sent.
- Hold the Home Assistant physical-action queue for 500 ms after each `ACK3`.
  This preserves every explicit button press without inventing repeat packets.
- Add regression coverage for the idle-session threshold and post-ACK holdoff.

## 0.1.4

- Add a diagnostic **Reconnect Controller** button that reinitializes the
  capture-backed session without sending a bed movement or massage action.
- Keep timeout recovery safe: a timed-out action is never resent automatically;
  the session is invalidated and the next explicit action reopens it.
- Add regression coverage for acknowledgement prefixes and controller endpoint
  validation.

## 0.1.3

- Add the capture-derived 10 ms settling interval after `ACKFE` and before the
  first direct action in a controller session.
- Keep the session opener one-shot and invalidate the session after an action
  acknowledgement timeout.
- Add regression coverage preventing the 500 ms repeat interval from being
  confused with the opener-to-action settling interval.

## 0.1.1

- Remove the unverified `LOGICDATAOPEN` preamble and 500 ms delay.
- Send only an observed direct nine-byte command and require `ACK3`.
- Repair the button entity description so all 20 action buttons can load.
- Add transport diagnostics without recording addresses or raw command bytes.

## 0.1.0 - 2026-09-21

Initial public pilot release.

### Added

- UI configuration for a compatible UDP adjustable-bed controller.
- Buttons for lift, flat, memory positions, massage adjustment, massage modes,
  and massage stop.
- Requested 0-10 massage intensity controls for head, lumbar, and leg zones.
- Last-requested action indicators that do not misrepresent physical state.
- Protocol tests, Home Assistant metadata validation, security policy, and
  HACS custom-repository installation instructions.

### Safety and limits

- The controller protocol has no validated physical-state query, encryption,
  or authentication.
- This pilot is for a trusted local network and requires hands-on validation
  before automations or voice-assistant exposure.

## 0.1.2

- Restore the capture-backed `FELOGICDATAOPEN` session initialization.
- Send the session opener once per Home Assistant transport session and wait for
  `ACKFE` before sending direct actions.
- Invalidate the session after an action acknowledgement timeout without
  blindly retrying the action.
- Add packet-level debug logging and protocol regression coverage.
- Do not add an unverified 500 ms wire delay or automatic action repetition.
