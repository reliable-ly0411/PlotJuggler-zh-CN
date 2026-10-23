// SPDX-License-Identifier: MPL-2.0
#pragma once

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <fcntl.h>
#include <io.h>
#include <windows.h>

#include <cstdio>
#endif

namespace PJ {
// A GUI subsystem executable must never allocate a console on an Explorer launch.
// Preserve redirected pipes/files (CI/QProcess), or adopt an existing parent console.
inline void attachParentConsoleStreams() {
#ifdef _WIN32
  const HANDLE stdout_handle = GetStdHandle(STD_OUTPUT_HANDLE);
  const HANDLE stderr_handle = GetStdHandle(STD_ERROR_HANDLE);
  const auto valid = [](HANDLE handle) {
    return handle != nullptr && handle != INVALID_HANDLE_VALUE && GetFileType(handle) != FILE_TYPE_UNKNOWN;
  };
  AttachConsole(ATTACH_PARENT_PROCESS);
  const auto bind = [&](HANDLE inherited, DWORD kind, FILE* stream, const char* console_name) {
    HANDLE handle = valid(inherited) ? inherited : GetStdHandle(kind);
    if (!valid(handle)) {
      return;
    }
    HANDLE duplicate = nullptr;
    if (!DuplicateHandle(
            GetCurrentProcess(), handle, GetCurrentProcess(), &duplicate, 0, FALSE, DUPLICATE_SAME_ACCESS)) {
      return;
    }
    const int fd = _open_osfhandle(reinterpret_cast<intptr_t>(duplicate), _O_TEXT);
    if (fd < 0) {
      CloseHandle(duplicate);
      return;
    }
    // GUI CRT streams can have descriptor -2, so first create a valid stream slot.
    if (_fileno(stream) < 0) {
      FILE* reopened = nullptr;
      freopen_s(&reopened, console_name, "w", stream);
    }
    if (_fileno(stream) >= 0) {
      _dup2(fd, _fileno(stream));
      setvbuf(stream, nullptr, _IONBF, 0);
    }
    _close(fd);
  };
  bind(stdout_handle, STD_OUTPUT_HANDLE, stdout, "NUL");
  bind(stderr_handle, STD_ERROR_HANDLE, stderr, "NUL");
#endif
}
}  // namespace PJ
