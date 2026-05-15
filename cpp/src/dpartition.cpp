// dpartition.cpp
// Расчёт кривой D-разбиения для крутильных колебаний расточной борштанги.
// Реализует формулу (10) из отчёта:
//   delta_hat = -p - lambda1 * sqrt(1 + delta1 * p) * coth(lambda2 * p / sqrt(1 + delta1 * p))
// где p = i*omega, lambda1 = sqrt(rho * G * Jp) / Jr, lambda2 = L * sqrt(rho / G).
//
// Использование:
//   dpartition rho G R_out R_in r_out r_in l_head Jr delta1 L omega_min omega_max N
//
// Все параметры числовые. Программа печатает в stdout строки вида
//   omega Re Im
// по одной точке на строку, разделённые пробелом.

#include <iostream>
#include <complex>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <string>

using cd = std::complex<double>;

// Гиперболический котангенс комплексного аргумента.
// Для больших |Re(z)| cosh и sinh переполняются по отдельности, но их
// отношение остаётся конечным (стремится к sign(Re(z))). Используем
// стандартное std::tanh от комплексного аргумента: cmath реализует его
// устойчиво, и coth(z) = 1 / tanh(z).
static cd ccoth(const cd& z) {
    cd t = std::tanh(z);
    // Защита от деления на ноль (tanh(0) = 0). В нашей задаче p = i*omega
    // не обращает аргумент в строгий ноль для omega != 0, но подстрахуемся.
    const double eps = 1e-300;
    if (std::abs(t) < eps) {
        return cd(0.0, 0.0);
    }
    return cd(1.0, 0.0) / t;
}

int main(int argc, char* argv[]) {
    if (argc != 14) {
        std::cerr << "Usage: " << argv[0]
                  << " rho G R_out R_in r_out r_in l_head Jr delta1"
                     " L omega_min omega_max N\n";
        return 1;
    }

    // Считываем параметры в том же порядке, что и в Usage.
    int idx = 1;
    double rho     = std::atof(argv[idx++]);  // плотность материала, кг/м^3
    double G       = std::atof(argv[idx++]);  // модуль сдвига, Па
    double R_out   = std::atof(argv[idx++]);  // внешний радиус борштанги, м
    double R_in    = std::atof(argv[idx++]);  // внутренний радиус борштанги, м
    double r_out   = std::atof(argv[idx++]);  // внешний радиус режущей головки, м
    double r_in    = std::atof(argv[idx++]);  // внутренний радиус режущей головки, м
    double l_head  = std::atof(argv[idx++]);  // длина режущей головки, м
    double Jr_in   = std::atof(argv[idx++]);  // момент инерции головки Jr, кг*м^2
                                              // (если <=0 — посчитаем сами)
    double delta1  = std::atof(argv[idx++]);  // коэф. внутреннего трения
    double L       = std::atof(argv[idx++]);  // длина борштанги, м
    double w_min   = std::atof(argv[idx++]);  // минимальная omega, рад/с
    double w_max   = std::atof(argv[idx++]);  // максимальная omega, рад/с
    int    N       = std::atoi(argv[idx++]);  // число точек по omega

    if (N < 2) N = 2;

    // Полярный момент инерции сечения борштанги (труба):
    //   Jp = (pi / 2) * (R_out^4 - R_in^4)
    const double PI = 3.14159265358979323846;
    double Jp = 0.5 * PI * (std::pow(R_out, 4) - std::pow(R_in, 4));

    // Момент инерции режущей головки. Если пользователь задал
    // Jr вручную (Jr_in > 0), берём его; иначе считаем как массивный
    // цилиндр-трубу: m = rho * pi * (r_out^2 - r_in^2) * l_head,
    //                Jr = m * (r_out^2 + r_in^2) / 2.
    double Jr;
    if (Jr_in > 0.0) {
        Jr = Jr_in;
    } else {
        double m_head = rho * PI *
                        (r_out * r_out - r_in * r_in) * l_head;
        Jr = 0.5 * m_head * (r_out * r_out + r_in * r_in);
    }

    // Постоянные коэффициенты формулы (10).
    double lambda1 = std::sqrt(rho * G * Jp) / Jr;
    double lambda2 = L * std::sqrt(rho / G);

    // Метаданные в stderr — пригодятся для отладки и подписи графика.
    std::cerr << "Jp=" << Jp
              << " Jr=" << Jr
              << " lambda1=" << lambda1
              << " lambda2=" << lambda2
              << "\n";

    std::cout << std::scientific << std::setprecision(10);

    // Сканируем omega от w_min до w_max, N точек.
    // omega = 0 пропускаем (там coth расходится).
    for (int k = 0; k < N; ++k) {
        double omega = w_min + (w_max - w_min) * k / static_cast<double>(N - 1);
        if (std::abs(omega) < 1e-12) {
            // Пропускаем точку у нуля — там p -> 0 и coth -> бесконечности.
            continue;
        }

        cd p(0.0, omega);
        cd one(1.0, 0.0);

        cd s = std::sqrt(one + delta1 * p);                 // sqrt(1 + delta1*p)
        cd arg = lambda2 * p / s;                            // аргумент coth
        cd delta_hat = -p - lambda1 * s * ccoth(arg);

        std::cout << omega << " "
                  << delta_hat.real() << " "
                  << delta_hat.imag() << "\n";
    }

    return 0;
}
