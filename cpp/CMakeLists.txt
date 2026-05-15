cmake_minimum_required(VERSION 3.15)
project(dpartition LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# MSVC: включаем обработку исключений и оптимизацию в Release.
if(MSVC)
    add_compile_options(/EHsc)
endif()

add_executable(dpartition src/dpartition.cpp)

# Кладём собранный .exe в python/gui/, рядом с gui.py.
# Тогда gui.py сразу его находит без правок путей.
set_target_properties(dpartition PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY            "${CMAKE_SOURCE_DIR}/../python/gui"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG      "${CMAKE_SOURCE_DIR}/../python/gui"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE    "${CMAKE_SOURCE_DIR}/../python/gui"
)