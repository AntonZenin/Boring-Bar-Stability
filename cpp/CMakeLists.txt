cmake_minimum_required(VERSION 3.15)
project(boring_bar_core LANGUAGES CXX)

# Стандарт C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ВАЖНО: используем статическую линковку MSVC рантайма (/MT вместо /MD).
# Это предотвращает конфликт DLL с PyQt5, который тащит свои MSVCP140.dll и пр.
# Должно стоять ДО find_package и pybind11_add_module.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

# Находим Python (нужен для pybind11)
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Получаем путь к pybind11 через установленный пакет
execute_process(
    COMMAND ${Python_EXECUTABLE} -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_package(pybind11 CONFIG REQUIRED)

# Создаём pybind11 модуль
pybind11_add_module(boring_bar_core
    src/bindings.cpp
)

# Компиляторные опции для MSVC
if(MSVC)
    target_compile_options(boring_bar_core PRIVATE /W4 /utf-8)
endif()

# Куда положить готовый .pyd — в папку python, чтобы Python мог его импортировать
set_target_properties(boring_bar_core PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../python"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../python"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/../python"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/../python"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/../python"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/../python"
)
