# Changelog

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
