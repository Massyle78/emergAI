"""Tests for CDS Hooks card domain models."""

import pytest
from pydantic import ValidationError

from app.models.cds_hooks import (
    CdsCard,
    CdsHookResponse,
    CdsSource,
    CdsSuggestion,
)
from app.models.enums import CdsIndicator


class TestCdsSource:
    def test_valid_minimal(self):
        s = CdsSource(label="emergAI Triage Engine")
        assert s.url is None
        assert s.icon is None

    def test_valid_with_urls(self):
        s = CdsSource(
            label="emergAI",
            url="https://emergai.example.com",
            icon="https://emergai.example.com/icon.png",
        )
        assert s.url is not None

    def test_rejects_empty_label(self):
        with pytest.raises(ValidationError):
            CdsSource(label="")


class TestCdsSuggestion:
    def test_valid(self):
        s = CdsSuggestion(label="Order ECG")
        assert s.is_recommended is False
        assert s.uuid is None

    def test_recommended(self):
        s = CdsSuggestion(
            label="Administer aspirin",
            is_recommended=True,
        )
        assert s.is_recommended is True


class TestCdsCard:
    def test_valid_minimal(self):
        card = CdsCard(
            summary="Patient shows signs of cardiac distress",
            indicator=CdsIndicator.CRITICAL,
            source=CdsSource(label="emergAI"),
        )
        assert card.detail is None
        assert card.suggestions == []

    def test_valid_full(self):
        card = CdsCard(
            summary="Elevated vitals detected",
            detail="Heart rate 140bpm, SpO2 91%. Consider immediate evaluation.",
            indicator=CdsIndicator.WARNING,
            source=CdsSource(label="emergAI"),
            suggestions=[CdsSuggestion(label="Order vitals recheck")],
        )
        assert len(card.suggestions) == 1

    def test_rejects_empty_summary(self):
        with pytest.raises(ValidationError):
            CdsCard(
                summary="",
                indicator=CdsIndicator.INFO,
                source=CdsSource(label="emergAI"),
            )

    def test_rejects_summary_exceeding_140_chars(self):
        with pytest.raises(ValidationError):
            CdsCard(
                summary="A" * 141,
                indicator=CdsIndicator.INFO,
                source=CdsSource(label="emergAI"),
            )


class TestCdsHookResponse:
    def test_empty_cards(self):
        r = CdsHookResponse()
        assert r.cards == []

    def test_with_cards(self):
        card = CdsCard(
            summary="Test card",
            indicator=CdsIndicator.INFO,
            source=CdsSource(label="emergAI"),
        )
        r = CdsHookResponse(cards=[card])
        assert len(r.cards) == 1
