# Security policy

## Pilot threat model

This integration sends unencrypted UDP control frames to a configurable
controller address. The observed protocol provides acknowledgements but no
validated authentication, encryption, authorization, or physical-state
readback. It is suitable only for a trusted local network with access controls
appropriate for a device that can move a bed.

Do not expose the controller UDP port to the public internet. Avoid automations
that move the bed without a person able to observe and stop it.

## Reporting a vulnerability

Use this repository's private vulnerability-reporting feature when it is
available. Otherwise, do not include secrets, private addresses, packet
captures, or personal data in a public issue; open only a minimal issue that
requests a private contact channel.

## Supported versions

Only the most recent tagged pilot release will receive security fixes.
