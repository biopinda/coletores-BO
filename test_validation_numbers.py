"""
Script de validação rápida para os casos específicos mencionados:
- "V.C. Vilela (67)"
- "M. Emmerich 1007"
- "E. Santos 1092"

Este script testa a classificação e sanitização desses casos.
"""

from src.pipeline.classifier import Classifier
from src.models.contracts import ClassificationInput

def test_cases():
    """Testa os casos específicos do usuário"""

    # Casos de teste do usuário
    test_inputs = [
        "V.C. Vilela (67)",
        "M. Emmerich 1007",
        "E. Santos 1092",
        "Silva, J. 456",
        "A. Santos (123A)"
    ]

    print("="*80)
    print("TESTE DE VALIDACAO - Remocao de Numeros")
    print("="*80)
    print()

    # Teste com NER desabilitado (apenas regex)
    print("Teste 1: Com NER DESABILITADO (apenas regex)")
    print("-"*80)
    clf_no_ner = Classifier(use_ner_fallback=False)

    for test in test_inputs:
        result = clf_no_ner.classify(ClassificationInput(text=test))
        print(f"Input:      '{result.original_text}'")
        print(f"Sanitized:  '{result.sanitized_text}'")
        print(f"Category:   {result.category.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Patterns:   {', '.join(result.patterns_matched)}")
        print()

    # Teste com NER habilitado (modelo BERTimbau-NER)
    print()
    print("Teste 2: Com NER HABILITADO (modelo bertimbau-ner)")
    print("-"*80)
    clf_with_ner = Classifier(use_ner_fallback=True, ner_model="bertimbau-ner")

    for test in test_inputs:
        result = clf_with_ner.classify(ClassificationInput(text=test))
        print(f"Input:      '{result.original_text}'")
        print(f"Sanitized:  '{result.sanitized_text}'")
        print(f"Category:   {result.category.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Patterns:   {', '.join(result.patterns_matched)}")
        print()

    print("="*80)
    print("VALIDACAO COMPLETA")
    print("="*80)
    print()
    print("Verificacoes importantes:")
    print("1. original_text deve conter os numeros")
    print("2. sanitized_text NAO deve conter numeros de colecao")
    print("3. Categoria deve ser 'Pessoa' (nao NAO_DETERMINADO)")
    print()


if __name__ == "__main__":
    test_cases()
