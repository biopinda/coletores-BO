"""Test script for fix.md issues - version 3"""

from src.models.entities import ClassificationCategory, EntityType
from src.models.schemas import ClassificationInput, NormalizationInput, AtomizationInput
from src.pipeline.classifier import Classifier
from src.pipeline.normalizer import Normalizer
from src.pipeline.atomizer import Atomizer
from src.pipeline.canonicalizer import Canonicalizer
from src.storage.local_db import LocalDatabase
import tempfile
import os


def test_leading_dot_removal():
    """Test: '. L. Azevedo, L.O.' should not have leading '.'"""
    normalizer = Normalizer()
    result = normalizer.normalize(NormalizationInput(original_name=". L. Azevedo, L.O."))

    print("Test 1: Leading dot removal")
    print(f"  Input: '. L. Azevedo, L.O.'")
    print(f"  Normalized: '{result.normalized}'")
    print(f"  Expected: Should not start with '.'")
    success = not result.normalized.startswith('.')
    print(f"  PASS" if success else f"  FAIL")
    print()
    return success


def test_full_name_to_initials():
    """Test: 'Alisson Nogueira Braz' should become 'Braz, A.N.'"""
    temp_db_path = tempfile.mktemp(suffix='.db')

    try:
        db = LocalDatabase(temp_db_path)
        canonicalizer = Canonicalizer(db)

        result = canonicalizer._format_canonicalName("ALISSON NOGUEIRA BRAZ", EntityType.PESSOA)

        print("Test 2: Full name to initials")
        print(f"  Input: 'ALISSON NOGUEIRA BRAZ'")
        print(f"  Output: '{result}'")
        print(f"  Expected: 'Braz, A.N.'")
        print(f"  PASS" if result == "Braz, A.N." else f"  FAIL")
        print()

        db.close()
        return result == "Braz, A.N."
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


def test_et_al_in_canonical():
    """Test: 'Botelho, R.D. ET. AL.' should extract only 'Botelho, R.D.'"""
    atomizer = Atomizer()
    result = atomizer.atomize(
        AtomizationInput(
            text="Botelho, R.D. ET. AL.",
            category=ClassificationCategory.CONJUNTO_PESSOAS
        )
    )

    print("Test 3: Et al. in canonical name")
    print(f"  Input: 'Botelho, R.D. ET. AL.'")
    print(f"  Atomized names: {[n.text for n in result.atomized_names]}")
    print(f"  Expected: ['Botelho, R.D.']")
    success = (len(result.atomized_names) == 1 and
               result.atomized_names[0].text == "Botelho, R.D.")
    print(f"  PASS" if success else f"  FAIL")
    print()
    return success


def test_complex_conjunto():
    """Test: 'Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré' is CONJUNTO_PESSOAS"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré")
    )

    print("Test 4: Complex conjunto")
    print(f"  Input: 'Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.CONJUNTO_PESSOAS}")
    print(f"  PASS" if result.category == ClassificationCategory.CONJUNTO_PESSOAS else f"  FAIL")
    print()
    return result.category == ClassificationCategory.CONJUNTO_PESSOAS


def test_initials_first_format():
    """Test: 'D.R. Gonzaga' should become 'Gonzaga, D.R.'"""
    temp_db_path = tempfile.mktemp(suffix='.db')

    try:
        db = LocalDatabase(temp_db_path)
        canonicalizer = Canonicalizer(db)

        result = canonicalizer._format_canonicalName("D.R. GONZAGA", EntityType.PESSOA)

        print("Test 5: Initials-first format")
        print(f"  Input: 'D.R. GONZAGA'")
        print(f"  Output: '{result}'")
        print(f"  Expected: 'Gonzaga, D.R.'")
        print(f"  PASS" if result == "Gonzaga, D.R." else f"  FAIL")
        print()

        db.close()
        return result == "Gonzaga, D.R."
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


def test_first_name_with_initial():
    """Test: 'Débora G. Takaki' should become 'Takaki, D.G.'"""
    temp_db_path = tempfile.mktemp(suffix='.db')

    try:
        db = LocalDatabase(temp_db_path)
        canonicalizer = Canonicalizer(db)

        result = canonicalizer._format_canonicalName("DÉBORA G. TAKAKI", EntityType.PESSOA)

        print("Test 6: First name with middle initial")
        print(f"  Input: 'DÉBORA G. TAKAKI'")
        print(f"  Output: '{result}'")
        print(f"  Expected: 'Takaki, D.G.'")
        print(f"  PASS" if result == "Takaki, D.G." else f"  FAIL")
        print()

        db.close()
        return result == "Takaki, D.G."
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


def test_two_people_comma_separated():
    """Test: 'Fernandes, F. M, Nogueira, J. B' should be CONJUNTO_PESSOAS"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="Fernandes, F. M, Nogueira, J. B")
    )

    print("Test 7: Two people comma-separated")
    print(f"  Input: 'Fernandes, F. M, Nogueira, J. B'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.CONJUNTO_PESSOAS}")
    print(f"  PASS" if result.category == ClassificationCategory.CONJUNTO_PESSOAS else f"  FAIL")
    print()
    return result.category == ClassificationCategory.CONJUNTO_PESSOAS


def test_et_al_variation():
    """Test: 'G.M. Antar Et. Al.' should extract only 'G.M. Antar'"""
    atomizer = Atomizer()
    result = atomizer.atomize(
        AtomizationInput(
            text="G.M. Antar Et. Al.",
            category=ClassificationCategory.CONJUNTO_PESSOAS
        )
    )

    print("Test 8: Et. Al. variation")
    print(f"  Input: 'G.M. Antar Et. Al.'")
    print(f"  Atomized names: {[n.text for n in result.atomized_names]}")
    print(f"  Expected: Only 'G.M. Antar' (et al removed)")
    success = (len(result.atomized_names) == 1 and
               "Et. Al" not in result.atomized_names[0].text and
               "G.M. Antar" in result.atomized_names[0].text)
    print(f"  PASS" if success else f"  FAIL")
    print()
    return success


if __name__ == "__main__":
    print("=" * 70)
    print("Testing fixes from docs/fix.md (v3)")
    print("=" * 70)
    print()

    results = []
    results.append(test_leading_dot_removal())
    results.append(test_full_name_to_initials())
    results.append(test_et_al_in_canonical())
    results.append(test_complex_conjunto())
    results.append(test_initials_first_format())
    results.append(test_first_name_with_initial())
    results.append(test_two_people_comma_separated())
    results.append(test_et_al_variation())

    print("=" * 70)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 70)

    exit(0 if all(results) else 1)
