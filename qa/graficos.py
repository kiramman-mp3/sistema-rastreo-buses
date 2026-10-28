"""Figures of the quality report, drawn from the evidence files (matplotlib)."""
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from common import OUT  # noqa: E402

FIG = os.path.abspath(os.path.join(OUT, os.pardir, 'figuras'))
INK, GREEN, YELLOW, RED, GREY = '#1f2a30', '#1e5560', '#e0a800', '#c0392b', '#9aa5ab'
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 9,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': INK})


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)
    return path


def error_rate(sets):
    """sets: list of (label, tests, failures)."""
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    labels = ['%s\n(%d pruebas)' % (s[0], s[1]) for s in sets]
    values = [100.0 * s[2] / s[1] for s in sets]
    bars = ax.bar(labels, values, color=[GREEN if v < 10 else YELLOW if v <= 30 else RED for v in values], width=0.55)
    ax.axhline(10, color=INK, lw=0.8, ls='--')
    ax.text(len(sets) - 0.5, 10.4, 'límite aceptable: 10 %', ha='right', fontsize=8)
    for bar, value, s in zip(bars, values, sets):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.4, ('%.2f %% (%d)' % (value, s[2])).replace('.', ','),
                ha='center', fontsize=8)
    ax.set_ylabel('% de error')
    ax.set_ylim(0, max(15, max(values) * 1.3))
    return _save(fig, 'error_por_conjunto.png')


def times_by_scenario(rows):
    """rows: list of (label, mean, stdev, p95)."""
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = [r[0] for r in rows][::-1]
    means = [r[1] for r in rows][::-1]
    sds = [r[2] for r in rows][::-1]
    ax.barh(labels, means, xerr=sds, color=GREEN, ecolor=INK, capsize=2, height=0.55)
    ax.axvline(0.5, color=INK, lw=0.8, ls='--')
    ax.text(0.51, -0.45, 'adecuado < 0,5 s', fontsize=8, va='bottom')
    ax.set_xlabel('Tiempo de respuesta medio (s), con barra de desviación estándar')
    ax.set_xlim(left=0)
    return _save(fig, 'tiempos_por_escenario.png')


def histogram(times, p95, mean):
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.hist(times, bins=40, color=GREEN)
    ax.axvline(mean, color=INK, lw=1, label=('media %.3f s' % mean).replace('.', ','))
    ax.axvline(p95, color=RED, lw=1, ls='--', label=('p95 %.3f s' % p95).replace('.', ','))
    ax.set_xlabel('Tiempo de respuesta (s)')
    ax.set_ylabel('Peticiones')
    ax.legend(frameon=False)
    return _save(fig, 'histograma_auditoria.png')


def pareto(causes):
    """causes: list of (label, count) sorted by count."""
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    labels = [c[0] for c in causes]
    counts = [c[1] for c in causes]
    total = sum(counts)
    ax.bar(range(len(counts)), counts, color=GREEN, width=0.55)
    ax2 = ax.twinx()
    cumulative, running = [], 0
    for c in counts:
        running += c
        cumulative.append(100.0 * running / total)
    ax2.plot(range(len(counts)), cumulative, color=YELLOW, marker='o')
    ax2.set_ylim(0, 105)
    ax2.set_ylabel('% acumulado')
    ax2.spines['right'].set_visible(True)
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel('Fallos')
    return _save(fig, 'pareto.png')


def coverage(rows):
    """rows: list of (file, percent)."""
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(6.4, 0.22 * len(rows) + 0.8))
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=[GREEN if r[1] >= 80 else YELLOW if r[1] >= 50 else RED for r in rows], height=0.6)
    ax.axvline(80, color=INK, lw=0.8, ls='--')
    ax.set_xlim(0, 105)
    ax.set_xlabel('Cobertura de líneas y ramas (%)')
    ax.tick_params(axis='y', labelsize=7.5)
    return _save(fig, 'cobertura.png')
