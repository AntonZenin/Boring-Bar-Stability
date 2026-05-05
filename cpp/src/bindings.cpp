// bindings.cpp
// На этом этапе — простой тестовый модуль с функцией add(a, b).
// Цель — убедиться, что связка C++ <-> pybind11 <-> Python работает.
// Позже сюда добавим математику D-разбиения.

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Тестовая функция: складывает два числа
double add(double a, double b) {
    return a + b;
}

// Тестовая функция: возвращает строку с приветствием
std::string hello() {
    return "C++ module is alive!";
}

// Регистрация модуля. Имя 'boring_bar_core' должно совпадать с именем в CMakeLists.txt
PYBIND11_MODULE(boring_bar_core, m) {
    m.doc() = "Boring bar stability analysis core (C++ via pybind11)";

    m.def("add", &add, "Add two numbers",
          py::arg("a"), py::arg("b"));

    m.def("hello", &hello, "Returns a greeting from C++");
}
