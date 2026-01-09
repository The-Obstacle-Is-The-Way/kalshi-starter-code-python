from __future__ import annotations

from kalshi_research.news.sentiment import SentimentAnalyzer


def test_sentiment_positive_keywords_are_positive() -> None:
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(
        "Analysts see strong momentum as prices rally and growth accelerates.",
        title="Breakthrough approval fuels rally",
    )
    assert result.label == "positive"
    assert result.score > 0.1
    assert result.confidence >= 0.5


def test_sentiment_negative_keywords_are_negative() -> None:
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(
        "Markets plunge amid fear and uncertainty. Traders worry about downside risk.",
        title="Crash concerns grow",
    )
    assert result.label == "negative"
    assert result.score < -0.1
    assert result.confidence >= 0.5


def test_sentiment_neutral_when_no_keywords() -> None:
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze("This article discusses a topic without clear signals.")
    assert result.label == "neutral"
    assert result.score == 0.0
    assert 0.0 <= result.confidence <= 1.0


def test_sentiment_negation_skips_keyword() -> None:
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze("This is not bullish. Traders are not optimistic.")
    # Both "bullish" and "optimistic" are negated, so confidence should be low/neutral.
    assert result.label == "neutral"
