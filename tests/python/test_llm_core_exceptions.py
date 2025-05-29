# tests/python/test_llm_core_exceptions.py
import pytest
from scripts.llm_core.exceptions import MissingEssentialFileAbort

def test_missing_essential_file_abort_exception():
    """Testa se a exceção MissingEssentialFileAbort pode ser levantada e capturada."""
    message = "Arquivo essencial 'test.txt' não encontrado."
    with pytest.raises(MissingEssentialFileAbort) as excinfo:
        raise MissingEssentialFileAbort(message)
    assert str(excinfo.value) == message

def test_missing_essential_file_abort_is_exception():
    """Verifica se MissingEssentialFileAbort é uma subclasse de Exception."""
    assert issubclass(MissingEssentialFileAbort, Exception)

def test_missing_essential_file_abort_no_message():
    """Testa a exceção sem uma mensagem específica."""
    with pytest.raises(MissingEssentialFileAbort):
        raise MissingEssentialFileAbort()