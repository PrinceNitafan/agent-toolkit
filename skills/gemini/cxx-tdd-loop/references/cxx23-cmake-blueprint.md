# C++23 & Modern CMake Reference Blueprint

Canonical target-centric CMake 3.28+ and C++23 layout for native projects (WSL2 `ext4` or Windows with Clang/GCC) with strict `-Werror` and ASan/UBSan test verification.

## 1. Root `CMakeLists.txt` Pattern

```cmake
cmake_minimum_required(VERSION 3.28)
project(domain_engine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(project_warnings INTERFACE)
target_compile_options(project_warnings INTERFACE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion
    -Wshadow -Wnon-virtual-dtor -Wold-style-cast -Werror
)

option(ENABLE_SANITIZERS "Enable ASan and UBSan for debug/test builds" OFF)
if(ENABLE_SANITIZERS)
    target_compile_options(project_warnings INTERFACE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(project_warnings INTERFACE -fsanitize=address,undefined)
endif()

add_library(domain_core STATIC src/record_parser.cpp)
target_include_directories(domain_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_link_libraries(domain_core PRIVATE project_warnings)

enable_testing()
find_package(GTest CONFIG REQUIRED)
add_executable(domain_core_tests tests/record_parser_test.cpp)
# Imported targets (GTest::gtest_main) mark interface includes as SYSTEM automatically.
target_link_libraries(domain_core_tests PRIVATE domain_core project_warnings GTest::gtest_main)
add_test(NAME domain_core_tests COMMAND domain_core_tests)
```

## 2. Narrow C++23 Contract (`include/domain/record_parser.hpp`)

```cpp
#pragma once

#include <concepts>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <span>
#include <string_view>

namespace domain {

enum class ParseError : std::uint8_t { EmptyPayload, InvalidHeader, ChecksumMismatch };

struct ParsedRecord {
    std::string_view key;
    std::uint64_t timestamp_ns;
};

template <typename Sink>
concept RecordSink = requires(Sink& sink, std::string_view key, std::uint64_t timestamp_ns) {
    { sink.on_record(key, timestamp_ns) } -> std::same_as<std::expected<void, ParseError>>;
};

// Non-template parser implemented in src/record_parser.cpp so domain_core builds as a static library.
[[nodiscard]] std::expected<ParsedRecord, ParseError> parse_next_record(
    std::span<const std::byte>& remaining
) noexcept;

template <RecordSink Sink>
[[nodiscard]] std::expected<std::size_t, ParseError> parse_batch(
    std::span<const std::byte> payload,
    Sink& sink
) {
    if (payload.empty()) {
        return std::unexpected(ParseError::EmptyPayload);
    }

    std::size_t count = 0;
    while (!payload.empty()) {
        const auto record = parse_next_record(payload);
        if (!record) {
            return std::unexpected(record.error());
        }
        if (const auto status = sink.on_record(record->key, record->timestamp_ns); !status) {
            return std::unexpected(status.error());
        }
        ++count;
    }
    return count;
}

}  // namespace domain
```

## 3. Static Library Implementation (`src/record_parser.cpp`)

```cpp
#include "domain/record_parser.hpp"

#include <cstddef>
#include <cstdint>

namespace domain {

std::expected<ParsedRecord, ParseError> parse_next_record(
    std::span<const std::byte>& remaining
) noexcept {
    if (remaining.size() < 1U + sizeof(std::uint64_t)) {
        return std::unexpected(ParseError::InvalidHeader);
    }

    const auto key_len = std::to_integer<std::size_t>(remaining.front());
    const std::size_t frame_len = 1U + key_len + sizeof(std::uint64_t);
    if (key_len == 0U || remaining.size() < frame_len) {
        return std::unexpected(ParseError::InvalidHeader);
    }

    const auto key_bytes = remaining.subspan(1U, key_len);
    const std::string_view key{reinterpret_cast<const char*>(key_bytes.data()), key_bytes.size()};

    std::uint64_t timestamp_ns = 0;
    const auto ts_bytes = remaining.subspan(1U + key_len, sizeof(std::uint64_t));
    for (std::size_t i = 0; i < sizeof(std::uint64_t); ++i) {
        timestamp_ns |= std::to_integer<std::uint64_t>(ts_bytes[i]) << (i * 8U);
    }

    remaining = remaining.subspan(frame_len);
    return ParsedRecord{.key = key, .timestamp_ns = timestamp_ns};
}

}  // namespace domain
```

## 4. Build & Sanitizer Commands

```bash
cmake -B build -G Ninja -DENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```
