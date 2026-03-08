# Biometric Integration

Biometric Integration is a Frappe app that connects Hikvision biometric terminals to your HR attendance process.

It is designed for teams that want to stop maintaining attendance in spreadsheets and move to a reliable, device-driven process with clear review points for HR.

## What this app helps you do in real work

In a normal office setup, employees punch in and punch out from a Hikvision terminal. This app brings those events into Frappe and organizes them as daily attendance logs per employee.

From the settings screen, HR or IT can first test whether the terminal is reachable. This avoids wasting time on sync attempts when network credentials or device access are not correct.

When connection is ready, attendance can be synced for any date and time range. This is useful in two common cases:
- daily operations, where you pull the latest records;
- recovery situations, where you re-sync a past window after downtime.

The app also has scheduled sync support, so recent attendance can be pulled automatically without a person manually running sync every day.

Device communication uses digest authentication against Hikvision ISAPI endpoints. In practice, this means you can use standard device credentials while keeping communication aligned with the device API model.

During sync, the app creates or updates daily attendance logs and avoids saving duplicate punches for the same time. This keeps records clean when the same period is synced more than once.

If employee names are available on the device, the app can fetch and store those names in attendance logs for better readability. There is also a utility to update employee name on the device from inside the app when naming needs correction.

## Handling exceptions (manual punches)

Real attendance operations always include exceptions: missed punches, hardware access issues, or late corrections approved by HR.

For these cases, the app supports manual punch entry linked to Employee records. The same manual entry can be edited later (date/time replacement flow) and deleted safely, with linked punch rows removed from attendance logs.

There is also a bulk update utility that rebuilds attendance logs from existing manual punch records. This is helpful when you need to normalize data after multiple manual corrections.

Punches are stored with type context (Auto or Manual), so report readers can quickly understand whether an event came from device sync or HR correction.

## Reporting and visibility

The app includes practical reports for daily and monthly review:

- Biometric Daily Report: punch sequence, total worked duration, and early-leave indicator, with visibility for absent active employees.
- Biometric Monthly Report: day-wise duration and monthly totals in both HH:MM and decimal hours.
- Biometric Manual Punch Report: available in the app structure but currently disabled.

## Data model used

Core doctypes available in this app:
- Biometric Integration Settings (single doctype)
- Biometric Attendance Log
- Biometric Attendance Punch Table (child)
- Biometric Manual Punch
- Attendance Leave Log
- Biometric Attendance Leave Table (child)

The workspace includes shortcuts for these doctypes and reports so HR users can access regular tasks from one place.

## Requirements

To run this smoothly in production:
- Frappe or ERPNext environment with this app installed.
- Hikvision terminal IP, username, and password.
- Employee records mapped with `attendance_device_id`.

## Supported devices

This app targets Hikvision terminals that expose the ISAPI access-control endpoints used by the sync process. The following models are included in the validated list from implementation testing:

ACT-T1331RU, ACT-T1331WRU, ACT-T1341MFRU, ACT-T1341MRU, ACT-T1331, ACT-T1331W, DS-K1A330, DS-K1A340FWX, DS-K1A340FX, DS-K1A340WX, DS-K1A340WX#India, DS-K1A340X, DS-K1T331, DS-K1T331W, DS-K1T341A, DS-K1T341AM, DS-K1T341AM-S, DS-K1T341AMF, DS-K1T341AMF-S, DS-K1T341AMHUN#India, DS-K1T341B, DS-K1T341BMI-T, DS-K1T341BMW, DS-K1T341BMWI-T, DS-K1T341CM, DS-K1T341CMF, DS-K1T341CMFW, DS-K1T341CMW, DS-K1T341M, DS-K1T342DWX, DS-K1T342DX, DS-K1T342EFWX, DS-K1T342EWX, DS-K1T342EX, DS-K1T342MFWX, DS-K1T342MFX, DS-K1T342MWX, DS-K1T342MX, DS-K1T343EFWX, DS-K1T343EFX, DS-K1T343EWX, DS-K1T343EX, DS-K1T343MFWX, DS-K1T343MFX, DS-K1T343MFX#India, DS-K1T343MWX, DS-K1T343MX, DS-K1T607, DS-K1T607E, DS-K1T607TEF#India, DS-K1T642, DS-K1T642E, DS-K1T642EF, DS-K1T642EFW, DS-K1T642EW, DS-K1T642M, DS-K1T642MF, DS-K1T642MFW, DS-K1T642MW, DS-K1T643MWX-T, DS-K1T643MX-T, DS-K1T671, DS-K1T671AM, DS-K1T671AMW, DS-K1T671BM, DS-K1T671BMF, DS-K1T671BMFW, DS-K1T671BMW, DS-K1T671BTM, DS-K1T671BTMF, DS-K1T671BTMFW, DS-K1T671BTMW, DS-K1T671M, DS-K1T671M#RUBB, DS-K1T671M#turkey, DS-K1T671M-L, DS-K1T671MF, DS-K1T671MF-L, DS-K1T671T, DS-K1T671TM, DS-K1T671TM-3XF, DS-K1T671TMF, DS-K1T671TMFW, DS-K1T671TMW, DS-K1T672, DS-K1T672DWX-T, DS-K1T672DX-T, DS-K1T672E, DS-K1T672M, DS-K1T672MW, DS-K1T673DWX, DS-K1T673DX, DS-K1T673TDGX, DS-K1T673TDWX, DS-K1T673TDX, DS-K1T680D, DS-K1T680D-E1, DS-K1T680DF, DS-K1T680DF-E1, DS-K1T680DFG, DS-K1T680DFW, DS-K1T680DG, DS-K1T680DW, DS-K1T690M-E1, DS-K1T690M-T, DS-K1T690MF-X, DS-K1T690MW, DS-K1T6Q-F71M, DS-K1T6QT-F72DWX, DS-K1T6QT-F72DX, DS-K1T6QT-F72TDGX, DS-K1T6QT-F72TDWX, DS-K1T6QT-F72TDX, DS-K1TA70MI-T, DS-K1TV41MF#Asia, DS-K5604A-3XF/V, DS-K5671-3XF/ZU, DS-K5671-W, DS-K5671-ZH, DS-K5671-ZU, DS-K5671-ZV, DS-K5671-ZV(B)#IN, DS-K5671A-ZU, DS-K5671B-ZH, DS-K5671B-ZU, DS-K5671B-ZV, DS-K5672MW-Z, VDP-T331#CATC, VDP-T341#CATC.
