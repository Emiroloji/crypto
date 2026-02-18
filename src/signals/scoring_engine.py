"""Signal scoring and validation engine"""

from typing import Dict, Optional
from src.config.settings import settings
from src.config.constants import REGIME_THRESHOLDS
from src.utils.logger import signal_logger


class ScoringEngine:
    """Validate and score trading signals"""
    
    def __init__(self):
        # NOTE: thresholds are read from settings at call time (not frozen here)
        # so that runtime configuration changes are respected.
        pass
    
    def validate_signal(self, signal_data: Dict) -> tuple[bool, str]:
        """
        Validate if signal meets trading criteria
        
        Args:
            signal_data: Signal information
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not signal_data:
            return False, "No signal data"
        
        # Read thresholds fresh from settings each call
        confidence_threshold = settings.confidence_threshold
        min_risk_reward = settings.min_risk_reward_ratio
        
        # Check confidence threshold
        confidence = signal_data.get('confidence_score', 0)
        if confidence < confidence_threshold:
            return False, f"Confidence {confidence:.1f}% below threshold {confidence_threshold}%"
        
        # Check risk/reward ratio
        rr_ratio = signal_data.get('risk_reward_ratio', 0)
        if rr_ratio < min_risk_reward:
            return False, f"R/R {rr_ratio:.2f} below minimum {min_risk_reward}"
        
        # Check for valid direction
        if not signal_data.get('direction'):
            return False, "No clear direction"
        
        # Check market regime (avoid extreme chop)
        market_regime = signal_data.get('market_regime', 'normal')
        trend_score = abs(signal_data.get('trend_score', 0))
        
        # If low volatility and weak trend, avoid trading
        if market_regime == 'low' and trend_score < 30:
            return False, "Low volatility with weak trend (chop condition)"
        
        signal_logger.info(
            f"Signal validated: {signal_data['symbol']} "
            f"Confidence: {confidence:.1f}% R/R: {rr_ratio:.2f}"
        )
        
        return True, "Signal valid"
    
    def calculate_signal_quality(self, signal_data: Dict) -> Dict:
        """
        Calculate signal quality metrics
        
        Args:
            signal_data: Signal information
            
        Returns:
            Dictionary with quality metrics
        """
        quality = {}
        
        # Component alignment score (how well components agree)
        scores = [
            signal_data.get('trend_score', 0),
            signal_data.get('momentum_score', 0),
            signal_data.get('volume_score', 0),
            signal_data.get('orderbook_score', 0),
        ]
        
        # Check if all scores have same sign (alignment)
        positive_count = sum(1 for s in scores if s > 0)
        negative_count = sum(1 for s in scores if s < 0)
        
        alignment_score = max(positive_count, negative_count) / len(scores) * 100
        quality['alignment_score'] = alignment_score
        
        # Strength score (average absolute value)
        strength_score = sum(abs(s) for s in scores) / len(scores)
        quality['strength_score'] = strength_score
        
        # Conviction score (confidence * alignment * strength)
        conviction = (
            signal_data.get('confidence_score', 0) *
            (alignment_score / 100) *
            (strength_score / 100)
        )
        quality['conviction_score'] = conviction
        
        # Risk score (lower is better)
        rr_ratio = signal_data.get('risk_reward_ratio', 0)
        risk_score = 100 - min(rr_ratio * 20, 100)  # Better R/R = lower risk
        quality['risk_score'] = risk_score
        
        # Overall quality grade
        if conviction > 80 and alignment_score > 75:
            quality['grade'] = 'A'
        elif conviction > 60 and alignment_score > 60:
            quality['grade'] = 'B'
        elif conviction > 40:
            quality['grade'] = 'C'
        else:
            quality['grade'] = 'D'
        
        return quality
    
    def get_position_priority(self, signal_data: Dict) -> int:
        """
        Get priority level for signal (1=highest, 5=lowest)
        
        Args:
            signal_data: Signal information
            
        Returns:
            Priority level
        """
        quality = self.calculate_signal_quality(signal_data)
        
        if quality['grade'] == 'A':
            return 1
        elif quality['grade'] == 'B':
            return 2
        elif quality['grade'] == 'C':
            return 3
        else:
            return 4


# Global scoring engine instance
scoring_engine = ScoringEngine()
