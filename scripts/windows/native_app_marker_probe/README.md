<!-- SPDX-License-Identifier: MPL-2.0 -->
# Native application marker preflight

This **read-only, Windows-only snapshot** is a gate for a controlled native test
launcher. It never calls `ActiveWidgetsMarker::take`, reads a marker's contents,
removes a record, stops a process, changes a profile, or writes to the default
marker location. It is not an OS sandbox and does not make the private test
profile isolate the production marker. It must be independently reviewed and
validated with the intended Windows toolchain before a launcher trusts it.

## Build

Build this directory standalone with the same **release** Qt Core and compiler
architecture as the test application. The CMake project obtains `PJ_QT_VERSION`
from the repository's `versions.env`, or accepts `-DPJ_QT_VERSION=<pinned
version>` when this directory is packaged separately. CMake requires that exact
Qt version. Use a clean build and preserve its log, executable, dependency
manifest and SHA-256 hashes. A non-Windows build deliberately returns exit 3; it
only supports the platform-independent policy tests, not native validation.

## CLI and binding

All six options are mandatory and can be supplied in any order, exactly once:

```
native_app_marker_probe.exe --expect-sid S-1-... --expect-session 1 \
  --expect-integrity-rid 8192 --expect-auth-luid 00000000:0123abcd \
  --expect-elevation-type limited --expect-qt-core C:/absolute/kit/Qt6Core.dll
```

The example is schematic, not a token to reuse. The invoking launcher must
independently obtain the **prospective app launch token**'s canonical user SID,
nonzero session ID, integrity RID (decimal), AuthenticationId LUID as eight hex
digits for each high/low half separated by a colon, and elevation type
(`default`, `full`, or `limited`). Those are compared against the probe's actual
primary token. The launcher must run the probe and subsequently create the app
with that same effective launch token, environment, and relevant user profile,
without thread impersonation, and must verify that the app was in fact created
with the intended identity. LocalSystem, LocalService and NetworkService SIDs,
session 0, process/token session mismatch, thread impersonation, AppContainer,
an unavailable token attribute, a nonempty `TokenRestrictedSids` list, or any
identity mismatch fails closed. The probe records only the count returned by
that query; zero does not prove a token has not been filtered or that its
privileges and groups match another token. This probe compares the listed
identity attributes, not all token privileges or groups. A nonzero session
does not prove a live interactive desktop, which the launcher must also
independently verify. Expected values must not be copied from the probe
response and then treated as independent evidence.

`--expect-qt-core` is the exact absolute drive path of the kit's Qt6Core.dll,
with no `.` or `..` components. The probe compares it case-insensitively with
the module path Windows actually loaded and requires that runtime and compiled
Qt versions match the pinned version. Independently verify the file hashes and
bind the application to the same DLL and loader environment. Comparing module
paths does not itself hash the DLL, establish the DLL used by a later process,
or prevent replacement after the check. In particular, place/run the probe so
the real loader resolves the intended kit DLL; do not assume PATH alone proves
this binding.

No option accepts a marker path. The probe sets the same organization and app
names as the shell (`PlotJuggler` and `PlotJuggler4`) and calls the real Qt
`QStandardPaths::writableLocation(AppLocalDataLocation)`. The launching process
must not alter the app's environment or Qt configuration between probe and app.

## What is inspected

* The exact Qt default location must be an absolute local fixed-volume drive
  path. Each existing component from the drive root is opened for attributes
  with reparse-point following disabled. It must be a directory, not a reparse
  point; its resolved path must match the expected component. An inaccessible,
  non-directory, reparse, alias, network/uncertain path, API error or failed
  enumeration is rejected. A missing path is accepted as empty only after the
  nearest existing parent has been successfully enumerated. No directory is
  created. These checks are snapshots, not handles held across app startup.
* Existing directory entries, including hidden, system, directory and reparse
  entries, are enumerated by metadata alone. The exact case-sensitive Qt regular
  expression `^active_widgets\.(\d+)\.json$` matches a record name. Any match
  is rejected, even if its numeric string overflows a PID or the entry is not
  an ordinary file. Other filenames do not match. Marker bytes are never read.
* A Windows Toolhelp process snapshot is enumerated system-wide. A different
  process is a candidate when its case-folded executable basename contains
  `plotjuggler` and ends in `.exe`, or equals `pj_app.exe`. Any candidate or
  snapshot/enumeration error is rejected. The result counts candidates, never
  their arguments or logs. A build renamed to an unrelated name is not
  identifiable by this rule; independently ensure none is running.

The probe does not lock anything. Another program can create a marker, replace a
path, or start PlotJuggler after the scan, including between the final check and
process creation. Neither a successful check nor a post-run check proves that
such races did not happen. The caller must control concurrent test activity and
should avoid other app launches while testing. Checking after a test detects
some residual state; it cannot undo an earlier change.

## Launcher contract

For **every actual app creation**, not just once per group:

1. Use a single serialized launcher with no overlapping app processes. Bind
   the intended token, environment, app and Qt DLL independently as above. Run
   the probe under that token immediately before the app. Save the raw UTF-8
   JSON and native process exit code.
2. Continue only when the process exits normally with code 0, stdout is one
   valid object with the expected schema, `ok` is true, JSON `exit_code` is 0,
   both enumeration fields are true, both counts are zero, and the identity,
   Qt and path evidence satisfies the independent launch binding. A missing,
   malformed, stale, truncated, mismatched, untrusted or failed result denies
   launch. Generic labels or previously saved JSON are never authorization.
3. Start and wait for the app in that same controlled context. Once it has
   exited, run the probe again immediately under the same binding, preserving
   its result. A nonzero or invalid post-check stops further launches and is
   reported; do not remove, repair or inspect unknown records automatically.

The caller must ensure no separate actor can start another app or change the
marker location during the test window as far as its operational controls
permit. This is a limitation, not a guarantee of race freedom.

## Output and exit codes

stdout is exactly one compact UTF-8 JSON object and a newline when writing
succeeds; stderr is not the evidence channel. Every response has schema
`pj-native-app-marker-probe/v1`, `ok` (boolean), `exit_code` (integer), `reason`
(machine-readable string), `platform`, `checked_at_utc` and `completed_at_utc`
(ISO 8601 UTC; these bracket collection), and `probe_pid`. The following
fields are null until reached, and must not be interpreted as clean when null:

* `token`: observed `sid`, `session`, `process_session`, `integrity_rid`,
  `auth_luid`, `elevation_type`, `restricting_sid_count`, and `app_container`.
  The count is from a successful `TokenRestrictedSids` query, not a general
  statement about token filtering or disabled privileges. On a successful
  response it is zero; a nonzero count or query failure refuses the launch.
* `qt`: observed `runtime_version`, `compiled_version`, and
  `core_module_path` (the object may be partial on failure).
* `marker_directory`: exact Qt-resolved path; `marker_directory_exists`:
  boolean; `marker_enumeration_ok`: boolean; `matching_marker_count`: integer.
  Missing path yields false/true/zero, respectively, only after its closest
  existing parent is enumerated successfully. A failed path check gives false
  enumeration status and null existence/count, because partial findings cannot
  certify emptiness.
* `process_enumeration_ok`: boolean; `other_app_process_count`: integer only
  when enumeration completed. If a marker already exists and the process
  enumeration also fails, the nonzero status remains a refusal and this field
  records the process failure even if `reason` names the marker first.

Exit 0 means the defined checks found a clean snapshot. Exit 2 means invalid
arguments, 3 unsupported OS, 4 token refusal, 5 Qt refusal, 6 path or marker
enumeration refusal, 7 one or more matching marker names, and 8 process
snapshot/enumeration failure or matching process. Exit 9 means JSON could not be
written completely; in that case the caller must not trust partial stdout.
Other abnormal exits also deny launch. The `reason` can carry a Win32 error
number for some path failures; do not infer a clean state from a particular
error string.

## Validation boundary

`marker_probe_policy` tests the exact matcher and failure policy using entries
created only inside its own `QTemporaryDir`. `marker_probe_unsupported` on
non-Windows asserts that such a binary cannot authorize a launch. Neither is a
Windows API test. The policy test also feeds synthetic four- and eight-byte
zero-count buffers, short and valid nonzero buffers, and an oversized count to
the restricting-SID count parser. Real Windows return lengths are recorded
by the identity test; the synthetic cases are not Windows API observations.

Windows builds additionally register these CTest cases:

* `marker_probe_windows_identity`: real token queries, independent eligibility
  facts and individually wrong SID, session, integrity, LUID and elevation
  expectations; three service-SID comparisons; an invalid token handle; and a
  newly created restricted token **handle** with a nonempty restricting-SID
  list. It never applies the token to a thread or process. A host token that is
  ineligible for the positive identity check makes the case skip. The service
  checks classify SID values, not actual service logons.
* `marker_probe_windows_qt`: the real loaded QtCore DLL path/version and a
  deliberately wrong expected path.
* `marker_probe_windows_cli`: launches the actual probe executable, checks
  invalid arguments and a separately acquired wrong-token expectation, and
  validates its native exit and single JSON object before a read-only positive
  check against the actual default path. The mismatch must exit before any
  marker-directory or process results are populated. A dirty, inaccessible or
  uncertain default path, existing candidate process, or ineligible token
  makes the positive case skip; it never creates a real default marker.
* `marker_probe_windows_marker_paths`: missing path, hidden/system marker,
  non-directory, and a junction under its own temporary root. Its injected
  `ERROR_ACCESS_DENIED` is explicitly a mock. The junction points only to
  another child of that root and is removed without traversing it.
* `marker_probe_windows_access_denied`: creates a fresh child with a DACL that
  denies the current SID `FILE_READ_ATTRIBUTES`, verifies a real Win32 open
  returns `ERROR_ACCESS_DENIED`, then checks the scanner refuses it. The DACL
  applies only at creation of this disposable child; no existing object, user
  account, system ACL, or security policy is changed. Cleanup touches only
  that child. If cleanup is uncertain the owned root is retained, not traversed.
* `marker_probe_windows_processes`: global snapshot plus a harmless owned
  short-lived executable whose name matches the candidate rule. It exits on
  stdin EOF. Other pre-existing candidates make this test skip. A test-only
  injected error after that child's match must make enumeration fail; partial
  results from failed enumeration are never accepted.

On Windows, collect normal CTest process status and JUnit (for example,
`ctest --output-on-failure --output-junit result.xml`). Each required exact
case name must pass exactly once; missing, failed or skipped cases are not
evidence of success. A case may return 77 (CTest skip) if a required owned
fixture cannot safely be exercised, such as junction creation or when the
current token bypasses the owned access-denial fixture. An actual skipped or
unrun case keeps its gate closed. Successful compilation and these focused
checks do not prove an active interactive desktop, comprehensive equality of
tokens, or coverage of every filtered-token form. In particular, a token
filtered only by disabled groups or deleted privileges may still have an empty
restricting-SID list.

No test accepts a directory argument, and no fixture path can be passed to the
production executable. Never create synthetic markers in the real default
location. Actual-default probing must stay read-only and must be checked with
the real launcher's token and Qt binding. Preserve build and test logs,
including failures. Windows MSVC/Qt, NTFS, process and token tests must actually
run before their results can be claimed.
