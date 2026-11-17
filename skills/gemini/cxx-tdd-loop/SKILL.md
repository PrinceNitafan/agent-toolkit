---
name: cxx-tdd-loop
description: "Execute a strict C++23 and Modern CMake Test-Driven Development (Red-Green-Refactor) loop with explicit dependency injection and zero-warning verification. Trigger with /cxx-tdd-loop."
---

# C++23 TDD Execution Loop (`/cxx-tdd-loop`)

Goal: deliver a verified C++23 change through a deterministic Red -> Green -> Zero-Warning Refactor loop ([cxx23-cmake-blueprint.md](references/cxx23-cmake-blueprint.md)). Every behavior change starts as a falsifiable test against an explicit interface contract.

## Core C++23 & Modern CMake Invariants
- **Language Standard**: Target C++23 (`-std=c++23`) with GNU extensions disabled (`CMAKE_CXX_STANDARD 23`, `CMAKE_CXX_STANDARD_REQUIRED ON`, `CMAKE_CXX_EXTENSIONS OFF`, `CMAKE_EXPORT_COMPILE_COMMANDS ON`).
- **C++23 Idioms**:
  - **Error Handling**: Use `std::expected<T, E>` for recoverable domain and I/O errors, and `std::optional<T>` for nullable values. Reserve exceptions for invariant-breaking faults at system boundaries.
  - **Zero-Copy Views**: Pass contiguous buffers and strings via `std::span<const T>`, `std::string_view`, and `std::mdspan` rather than owning containers unless ownership transfer is intended.
  - **Constrained Generics**: Constrain all templates with C++20/23 `concept` definitions and `requires` clauses (never legacy `std::enable_if` SFINAE).
  - **Compile-Time & Formatting**: Prefer `constexpr` and `consteval` for lookup tables and parsers; use `std::format` and `std::print` over `<iostream>` or `printf`.
  - **RAII & Lifetimes**: Manage heap ownership strictly through RAII (`std::unique_ptr`, custom deleters, or scoped value types). Ban raw owning `new`/`delete`, delete copy operations on resource classes (`ClassName(const ClassName&) = delete;`), and mark moves `noexcept`.
- **Target-Centric CMake (3.28+)**: Declare flags, includes, definitions, and links strictly per target (`target_compile_options()`, `target_include_directories()`, `target_link_libraries()`) with explicit `PRIVATE`, `PUBLIC`, or `INTERFACE` scopes. Never mutate global `CMAKE_CXX_FLAGS` or use directory-scoped `include_directories()` / `link_libraries()`.

## 1. Verify Environment & Target Boundaries
1. **Enforce Native Environment Execution**: In WSL2/hybrid setups, confirm the working directory is on native `ext4` (`/home/<username>/...`) and run `cmake`, `ninja`, `clang++`, `g++`, and `ctest` in WSL2 `bash`. On standalone Windows, run builds natively in PowerShell with your configured compiler/toolchain.
2. **Normalize Input Paths**: In WSL2, translate any Windows host path (such as `C:\Users\...` or `D:\...`) to `/mnt/<drive>/...` (or via `wslpath -u '<win_path>'`) before passing it to Linux commands.
3. **Inspect the Build Graph**: Read the relevant `CMakeLists.txt` and module headers (`file://` links) to identify the target library, its visibility scopes (`PRIVATE`, `PUBLIC`, `INTERFACE`), and its linked test executable.
4. **Check Assumptions**: If the contract has multiple valid designs with non-obvious lifetime, threading, or error-propagation trade-offs, stop and ask the user with `ask_question` before writing code.

## 2. Lock the Contract & Write the Failing Test (Red)
1. **Define the Narrow Contract**:
   - Declare or update the header interface using C++23 idioms: `std::expected<T, E>` for recoverable errors, `std::span<const T>` / `std::string_view` for non-owning views, and `concept` / `requires` constraints for templates.
   - Inject all external dependencies (clocks, allocators, loggers, I/O handles, thread pools) explicitly through constructors or function parameters. Ban singletons and hidden globals.
   - Provide a minimal compilable stub (for example, returning `std::unexpected(...)`) so the test target links cleanly.
2. **Write the Falsifiable Test**:
   - Add a focused unit test in the module's test target covering the happy path, boundary conditions, and expected error states.
   - Register any new test file in the module's `CMakeLists.txt` target sources.
3. **Verify the Red State**:
   Run the out-of-source build and execute the specific test in the active shell:
   ```bash
   cmake -B build -G Ninja -DCMAKE_CXX_STANDARD=23 -DCMAKE_CXX_STANDARD_REQUIRED=ON -DCMAKE_CXX_EXTENSIONS=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
   cmake --build build
   ctest --test-dir build --output-on-failure -R "<test_name_filter>"
   ```
   Confirm the new test compiles and fails on the assertion (not on a broken build environment).

## 3. Implement the Surgical Fix (Green)
1. **Write Minimum Viable C++23**:
   - Implement only the logic required to satisfy the contract and make the failing test pass.
   - Enforce strict RAII (`std::unique_ptr`, scoped handles, explicit `= delete` copy operations on resource types, `noexcept` moves).
   - Do not bundle unrelated refactors or unrequested features.
2. **Verify the Green State**:
   Recompile and run the targeted test, then the full module test suite:
   ```bash
   cmake --build build
   ctest --test-dir build --output-on-failure
   ```
   If any test fails, inspect the failure output, fix the root cause in the implementation, and re-run before moving to Step 4.

## 4. Zero-Warning & Sanitizer Gate (Refactor)
1. **Refactor Under Green**:
   - Eliminate internal duplication, tighten `constexpr` / `consteval` evaluation where applicable, and verify comments explain only non-obvious invariants.
2. **Enforce Zero Warnings**:
   - Verify the target compiles cleanly with zero warnings under strict flags:
     `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wnon-virtual-dtor -Wold-style-cast -Werror`.
   - Ensure any third-party headers are included via `target_include_directories(<target> SYSTEM ...)` rather than suppressing project warnings.
3. **Run Sanitizer Verification**:
   - When modifying memory management, concurrency, spans, or lifetimes, build and run tests with AddressSanitizer and UndefinedBehaviorSanitizer enabled (or use `--preset debug-asan` when `CMakePresets.json` is configured):
     ```bash
     cmake -B build-asan -G Ninja -DENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
     cmake --build build-asan
     ctest --test-dir build-asan --output-on-failure
     ```

## 5. Report Completion
Output a concise final report (under 8 lines):
- **Result**: What contract and behavior were implemented (with clickable `file://` links to headers, implementation, and tests).
- **Verification**: Exact `cmake` / `ctest` targets executed and their pass/warning status.
- **Open Decisions**: Any follow-up architectural questions or deferred items.
