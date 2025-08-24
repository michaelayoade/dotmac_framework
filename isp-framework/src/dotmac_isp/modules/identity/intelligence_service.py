"""Lightweight customer intelligence service for portal enhancements."""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from .service import CustomerService


class CustomerIntelligenceService:
    """Simple customer intelligence for immediate ROI."""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.customer_service = CustomerService(db, tenant_id)
    
    async def get_customer_health_scores(self) -> Dict[str, Any]:
        """Get customer health scores - simple calculation for immediate impact."""
        customers = await self.customer_service.list(filters={}, limit=1000, offset=0)
        
        health_scores = {}
        for customer in customers:
            # Simple health score based on status and service count
            score = 100  # Start at 100
            
            # Status-based scoring
            if customer.status == 'suspended':
                score = 20
            elif customer.status == 'pending':
                score = 60
            
            # Service count impact (more services = higher health)
            if hasattr(customer, 'services_count'):
                if customer.services_count == 0:
                    score = min(score, 40)
                elif customer.services_count >= 3:
                    score = min(score + 10, 100)
            
            # Age-based adjustment (newer customers need more attention)
            if hasattr(customer, 'created_at'):
                days_old = (datetime.utcnow() - customer.created_at).days
                if days_old < 30:  # New customer
                    score = max(score - 10, 0)
            
            health_scores[str(customer.id)] = {
                'score': score,
                'risk_level': 'high' if score < 40 else 'medium' if score < 70 else 'low',
                'churn_risk': score < 50
            }
        
        return {
            'customer_health': health_scores,
            'summary': {
                'total_customers': len(customers),
                'high_risk': len([s for s in health_scores.values() if s['risk_level'] == 'high']),
                'at_risk_count': len([s for s in health_scores.values() if s['churn_risk']]),
            }
        }
    
    async def get_churn_alerts(self) -> Dict[str, Any]:
        """Get customers at risk for immediate intervention."""
        health_data = await self.get_customer_health_scores()
        customers = await self.customer_service.list(filters={}, limit=1000, offset=0)
        
        churn_alerts = []
        for customer in customers:
            customer_id = str(customer.id)
            if customer_id in health_data['customer_health']:
                health_info = health_data['customer_health'][customer_id]
                if health_info['churn_risk']:
                    churn_alerts.append({
                        'customer_id': customer_id,
                        'customer_name': customer.name if hasattr(customer, 'name') else 'Unknown',
                        'health_score': health_info['score'],
                        'risk_level': health_info['risk_level'],
                        'recommended_action': self._get_recommended_action(health_info['score']),
                        'priority': 'urgent' if health_info['score'] < 30 else 'high'
                    })
        
        # Sort by priority and score
        churn_alerts.sort(key=lambda x: (x['priority'] == 'urgent', -x['health_score']))
        
        return {
            'churn_alerts': churn_alerts[:20],  # Top 20 most at-risk
            'total_at_risk': len(churn_alerts),
            'urgent_count': len([a for a in churn_alerts if a['priority'] == 'urgent'])
        }
    
    def _get_recommended_action(self, score: int) -> str:
        """Simple recommended actions based on health score."""
        if score < 30:
            return "Immediate contact - retention offer"
        elif score < 50:
            return "Proactive outreach - check satisfaction"
        elif score < 70:
            return "Service upsell opportunity"
        else:
            return "Monitor - stable customer"