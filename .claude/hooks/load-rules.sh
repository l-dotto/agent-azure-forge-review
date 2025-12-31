#!/bin/bash
# Script para carregar todas as regras do diretório .claude/rules automaticamente
# Este script é executado quando o Claude Code inicia

# Obtém o diretório do projeto dinamicamente (diretório pai de .claude)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"
RULES_DIR="$CLAUDE_DIR/rules"

echo "========================================"
echo "Carregando regras do projeto Mauro Resolve"
echo "========================================"
echo ""

# Verifica se o diretório de regras existe
if [ ! -d "$RULES_DIR" ]; then
    echo "Diretório de regras não encontrado: $RULES_DIR"
    exit 1
fi

# Carrega todas as regras .md no diretório
for file in "$RULES_DIR"/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "=== Carregando: $filename ==="
        cat "$file"
        echo ""
        echo ""
    fi
done

echo "========================================"
echo "Todas as regras foram carregadas!"
echo "Total de arquivos: $(ls -1 "$RULES_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')"
echo "========================================"