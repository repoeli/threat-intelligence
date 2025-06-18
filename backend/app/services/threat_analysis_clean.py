"""
Enhanced Threat Analysis Service
Combines multiple intelligence sources and provides unified threat scoring
"""

import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from ..models import (
    ThreatIntelligenceResult, 
    ThreatScore, 
    ThreatLevel, 
    IndicatorType, 
    AnalysisStatus,
    VendorResult,
    AnalysisMetadata
)
from ..services.virustotal_service import vt_call
from ..utils.indicator import determine_indicator_type

logger = logging.getLogger(__name__)


class ThreatAnalysisService:
    """Enhanced threat analysis service with unified scoring"""
    
    def __init__(self):
        self.threat_level_thresholds = {
            ThreatLevel.CRITICAL: 0.8,
            ThreatLevel.HIGH: 0.6,            ThreatLevel.MEDIUM: 0.4,
            ThreatLevel.LOW: 0.2,
            ThreatLevel.BENIGN: 0.0
        }
    
    async def analyze_indicator(
        self, 
        indicator: str, 
        user_id: str, 
        subscription: str,
        include_raw: bool = False,
        enhanced_analysis: bool = False,
        deep_analysis: bool = False
    ) -> ThreatIntelligenceResult:
        """Main analysis entry point"""
        start_time = time.time()
        
        # Determine indicator type
        indicator_type = self._get_indicator_type(indicator)
        
        # Create metadata
        metadata = AnalysisMetadata(
            analyzed_at=datetime.utcnow(),
            analysis_id=f"analysis_{int(time.time())}_{hash(indicator) % 10000}",
            sources_used=["virustotal"],
            cached=False
        )
        
        try:
            # Gather intelligence from multiple sources
            raw_responses = {}
            
            # VirusTotal analysis
            vt_data = await self._analyze_virustotal(indicator, indicator_type, user_id, subscription)
            raw_responses["virustotal"] = vt_data
            
            # AbuseIPDB for IPs
            if indicator_type == IndicatorType.IP:
                try:
                    abuse_data = await self._analyze_abuseipdb(indicator)
                    raw_responses["abuseipdb"] = abuse_data
                    metadata.sources_used.append("abuseipdb")
                except Exception as e:
                    logger.warning(f"AbuseIPDB analysis failed: {e}")
            
            # Process and score results
            threat_score = self._calculate_threat_score(raw_responses, indicator_type)
            vendor_results = self._extract_vendor_results(raw_responses)
            detection_ratio = self._calculate_detection_ratio(vendor_results)
              # Extract additional intelligence
            reputation, categories, tags = self._extract_reputation_data(raw_responses)
            first_seen, last_seen = self._extract_timeline_data(raw_responses)
            geolocation = self._extract_geolocation(raw_responses, indicator_type)
            
            # Enhanced analysis for premium users
            if enhanced_analysis:
                try:
                    # Add more detailed threat intelligence sources
                    if subscription in ["medium", "plus", "admin"]:
                        # Additional threat intel processing
                        enhanced_data = await self._perform_enhanced_analysis(
                            indicator, indicator_type, raw_responses
                        )
                        raw_responses.update(enhanced_data)
                        metadata.sources_used.extend(enhanced_data.keys())
                        
                        # Recalculate threat score with enhanced data
                        threat_score = self._calculate_threat_score(raw_responses, indicator_type, enhanced=True)
                except Exception as e:
                    logger.warning(f"Enhanced analysis failed: {e}")
            
            # Deep analysis for enterprise users
            if deep_analysis and subscription in ["plus", "admin"]:
                try:
                    deep_data = await self._perform_deep_analysis(
                        indicator, indicator_type, raw_responses
                    )
                    raw_responses.update(deep_data)
                    metadata.sources_used.extend(deep_data.keys())
                    
                    # Add deep analysis insights
                    categories.extend(deep_data.get("additional_categories", []))
                    tags.extend(deep_data.get("behavioral_tags", []))
                except Exception as e:
                    logger.warning(f"Deep analysis failed: {e}")
            
            # Complete metadata
            processing_time = int((time.time() - start_time) * 1000)
            metadata.processing_time_ms = processing_time
            
            # Build result
            result = ThreatIntelligenceResult(
                indicator=indicator,
                indicator_type=indicator_type,
                status=AnalysisStatus.COMPLETED,
                threat_score=threat_score,
                vendor_results=vendor_results,
                detection_ratio=detection_ratio,
                reputation=reputation,
                categories=categories,
                tags=tags,
                first_seen=first_seen,
                last_seen=last_seen,
                geolocation=geolocation,
                metadata=metadata,
                raw_responses=raw_responses if include_raw else {}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {indicator}: {e}")
            # Return failed analysis result
            metadata.processing_time_ms = int((time.time() - start_time) * 1000)
            return ThreatIntelligenceResult(
                indicator=indicator,
                indicator_type=indicator_type,
                status=AnalysisStatus.FAILED,
                threat_score=ThreatScore(
                    overall_score=0.0,
                    confidence=0.0,
                    threat_level=ThreatLevel.BENIGN,
                    factors={"error": str(e)}
                ),
                metadata=metadata
            )
    
    def _get_indicator_type(self, indicator: str) -> IndicatorType:
        """Convert string indicator type to enum"""
        type_mapping = {
            "ip": IndicatorType.IP,
            "domain": IndicatorType.DOMAIN,
            "url": IndicatorType.URL,
            "hash": IndicatorType.HASH,
            "email": IndicatorType.EMAIL
        }
        
        detected_type = determine_indicator_type(indicator)
        return type_mapping.get(detected_type, IndicatorType.DOMAIN)
    
    async def _analyze_virustotal(
        self, 
        indicator: str, 
        indicator_type: IndicatorType, 
        user_id: str, 
        subscription: str
    ) -> Dict[str, Any]:
        """Analyze indicator using VirusTotal"""
        
        endpoint_mapping = {
            IndicatorType.IP: ("get_ip_report", {"ip": indicator}),
            IndicatorType.DOMAIN: ("get_domain_report", {"domain": indicator}),
            IndicatorType.HASH: ("get_file_report", {"file_id": indicator}),
            IndicatorType.URL: (
                "get_url_report", 
                {"url_id": base64.urlsafe_b64encode(indicator.encode()).decode().rstrip("=")}
            )
        }
        
        if indicator_type not in endpoint_mapping:
            raise ValueError(f"Unsupported indicator type for VirusTotal: {indicator_type}")
        
        endpoint, path_params = endpoint_mapping[indicator_type]
        
        return await vt_call(
            user_id,
            subscription,
            endpoint,
            path_params=path_params
        )
    
    async def _analyze_abuseipdb(self, ip: str) -> Dict[str, Any]:
        """Analyze IP using AbuseIPDB"""
        # This would implement AbuseIPDB integration
        # For now, return mock data
        return {
            "data": {
                "abuseConfidenceScore": 0,
                "countryCode": "US",
                "usageType": "Data Center/Web Hosting/Transit",
                "isp": "Example ISP",
                "totalReports": 0,
                "numDistinctUsers": 0
            }
        }
    
    def _calculate_threat_score(
        self, 
        raw_responses: Dict[str, Any], 
        indicator_type: IndicatorType,
        enhanced: bool = False
    ) -> ThreatScore:
        """Calculate unified threat score from all sources"""
        factors = {}
        total_score = 0.0
        confidence_factors = []
        
        # VirusTotal scoring
        if "virustotal" in raw_responses:
            vt_score, vt_confidence = self._score_virustotal(raw_responses["virustotal"])
            factors["virustotal"] = vt_score
            total_score += vt_score * 0.7  # 70% weight for VT
            confidence_factors.append(vt_confidence)
        
        # AbuseIPDB scoring
        if "abuseipdb" in raw_responses:
            abuse_score, abuse_confidence = self._score_abuseipdb(raw_responses["abuseipdb"])
            factors["abuseipdb"] = abuse_score
            total_score += abuse_score * 0.3  # 30% weight for AbuseIPDB
            confidence_factors.append(abuse_confidence)
        
        # Calculate overall confidence
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
        
        # Determine threat level
        threat_level = ThreatLevel.BENIGN
        for level, threshold in sorted(self.threat_level_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if total_score >= threshold:
                threat_level = level
                break
        
        return ThreatScore(
            overall_score=min(total_score, 1.0),
            confidence=confidence,
            threat_level=threat_level,
            factors=factors
        )
    
    def _score_virustotal(self, vt_data: Dict[str, Any]) -> Tuple[float, float]:
        """Score VirusTotal results"""
        try:
            attributes = vt_data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            
            total_engines = malicious + suspicious + harmless + undetected
            
            if total_engines == 0:
                return 0.0, 0.0
            
            # Calculate score based on detection ratio
            detection_score = (malicious + suspicious * 0.5) / total_engines
            
            # Confidence based on number of engines
            confidence = min(total_engines / 70.0, 1.0)  # Assume 70 is max engines
            
            return detection_score, confidence
            
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def _score_abuseipdb(self, abuse_data: Dict[str, Any]) -> Tuple[float, float]:
        """Score AbuseIPDB results"""
        try:
            confidence_score = abuse_data.get("data", {}).get("abuseConfidenceScore", 0)
            score = confidence_score / 100.0  # Convert to 0-1 range
            confidence = 0.8 if confidence_score > 0 else 0.3  # Lower confidence than VT
            return score, confidence
        except (KeyError, TypeError):
            return 0.0, 0.0
    
    def _extract_vendor_results(self, raw_responses: Dict[str, Any]) -> List[VendorResult]:
        """Extract individual vendor results"""
        results = []
        
        # VirusTotal vendor results
        if "virustotal" in raw_responses:
            vt_data = raw_responses["virustotal"]
            try:
                scans = vt_data.get("data", {}).get("attributes", {}).get("last_analysis_results", {})
                for vendor, result in scans.items():
                    results.append(VendorResult(
                        vendor=vendor,
                        result=result.get("result", "clean"),
                        category=result.get("category"),
                        engine_version=result.get("engine_version")
                    ))
            except (KeyError, TypeError):
                pass
        
        return results
    
    def _calculate_detection_ratio(self, vendor_results: List[VendorResult]) -> str:
        """Calculate detection ratio string"""
        if not vendor_results:
            return "0/0"
        
        detections = sum(1 for result in vendor_results 
                        if result.result and result.result.lower() not in ["clean", "undetected"])
        total = len(vendor_results)
        
        return f"{detections}/{total}"
    
    def _extract_reputation_data(self, raw_responses: Dict[str, Any]) -> Tuple[Optional[str], List[str], List[str]]:
        """Extract reputation, categories, and tags"""
        reputation = None
        categories = []
        tags = []
        
        # Extract from VirusTotal
        if "virustotal" in raw_responses:
            vt_data = raw_responses["virustotal"]
            try:
                attributes = vt_data.get("data", {}).get("attributes", {})
                
                # Categories
                vt_categories = attributes.get("categories", {})
                categories.extend(vt_categories.values())
                
                # Tags
                vt_tags = attributes.get("tags", [])
                tags.extend(vt_tags)
                
                # Reputation based on stats
                stats = attributes.get("last_analysis_stats", {})
                malicious = stats.get("malicious", 0)
                if malicious > 0:
                    reputation = "malicious"
                elif stats.get("suspicious", 0) > 0:
                    reputation = "suspicious"
                else:
                    reputation = "clean"
                    
            except (KeyError, TypeError):
                pass
        
        return reputation, categories, tags
    
    def _extract_timeline_data(self, raw_responses: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract first seen and last seen dates"""
        first_seen = None
        last_seen = None
        
        if "virustotal" in raw_responses:
            vt_data = raw_responses["virustotal"]
            try:
                attributes = vt_data.get("data", {}).get("attributes", {})
                
                # Convert timestamps
                if "first_submission_date" in attributes:
                    first_seen = datetime.fromtimestamp(attributes["first_submission_date"])
                
                if "last_analysis_date" in attributes:
                    last_seen = datetime.fromtimestamp(attributes["last_analysis_date"])
                    
            except (KeyError, TypeError, OSError):
                pass
        
        return first_seen, last_seen
    
    def _extract_geolocation(self, raw_responses: Dict[str, Any], indicator_type: IndicatorType) -> Optional[Dict[str, Any]]:
        """Extract geolocation information"""
        if indicator_type != IndicatorType.IP:
            return None
        
        geo_data = {}
        
        # From VirusTotal
        if "virustotal" in raw_responses:
            vt_data = raw_responses["virustotal"]
            try:
                attributes = vt_data.get("data", {}).get("attributes", {})
                geo_data.update({
                    "country": attributes.get("country"),
                    "asn": attributes.get("asn"),
                    "as_owner": attributes.get("as_owner"),
                    "network": attributes.get("network")
                })
            except (KeyError, TypeError):
                pass
        
        # From AbuseIPDB
        if "abuseipdb" in raw_responses:
            abuse_data = raw_responses["abuseipdb"]
            try:
                data = abuse_data.get("data", {})
                geo_data.update({
                    "country_code": data.get("countryCode"),
                    "usage_type": data.get("usageType"),
                    "isp": data.get("isp")
                })
            except (KeyError, TypeError):
                pass
        
        return geo_data if geo_data else None

    async def _perform_enhanced_analysis(
        self, 
        indicator: str, 
        indicator_type: IndicatorType, 
        existing_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform enhanced analysis for premium users"""
        enhanced_data = {}
        
        try:
            # Simulate enhanced threat intel sources
            # In production, this would call additional APIs like:
            # - Recorded Future
            # - ThreatConnect  
            # - Anomali
            # - IBM X-Force
            
            enhanced_data["enhanced_intel"] = {
                "risk_score_adjustment": 0.1,
                "confidence_boost": 0.15,
                "additional_context": {
                    "threat_actor_attribution": "Unknown",
                    "campaign_association": "None detected",
                    "infrastructure_analysis": "Clean infrastructure"
                },
                "behavioral_indicators": [],
                "threat_hunting_rules": []
            }
            
            # Add simulated enhanced scoring factors
            vt_data = existing_data.get("virustotal", {})
            if vt_data:
                enhanced_data["enhanced_intel"]["advanced_heuristics"] = {
                    "submission_pattern_analysis": "Normal",
                    "prevalence_scoring": "Medium",
                    "temporal_analysis": "Stable"
                }
            
        except Exception as e:
            logger.warning(f"Enhanced analysis failed: {e}")
            
        return enhanced_data

    async def _perform_deep_analysis(
        self, 
        indicator: str, 
        indicator_type: IndicatorType, 
        existing_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform deep analysis for enterprise users"""
        deep_data = {}
        
        try:
            # Simulate deep analysis features
            # In production, this would include:
            # - Malware family classification
            # - APT group attribution
            # - Kill chain analysis
            # - Behavioral analysis
            # - Network topology analysis
            
            deep_data["deep_analysis"] = {
                "malware_family": "None detected",
                "apt_attribution": "No attribution",
                "kill_chain_stage": "Reconnaissance",
                "confidence_level": "High",
                "additional_categories": [],
                "behavioral_tags": ["benign", "legitimate"],
                "network_analysis": {
                    "hosting_provider": "Unknown",
                    "autonomous_system": "Unknown", 
                    "related_infrastructure": []
                },
                "temporal_analysis": {
                    "first_seen_global": None,
                    "activity_timeline": [],
                    "peak_activity_periods": []
                }
            }
            
            # Add deep analysis based on indicator type
            if indicator_type == IndicatorType.IP:
                deep_data["deep_analysis"]["ip_reputation"] = {
                    "proxy_detection": False,
                    "tor_exit_node": False,
                    "botnet_membership": False,
                    "scanning_activity": False
                }
            elif indicator_type in [IndicatorType.DOMAIN, IndicatorType.URL]:
                deep_data["deep_analysis"]["domain_analysis"] = {
                    "dga_detection": False,
                    "typosquatting": False,
                    "subdomain_enumeration": [],
                    "certificate_analysis": {}
                }
            elif indicator_type == IndicatorType.HASH:
                deep_data["deep_analysis"]["file_analysis"] = {
                    "packer_detection": "None",
                    "encryption_detected": False,
                    "code_similarity": [],
                    "yara_matches": []
                }
                
        except Exception as e:
            logger.warning(f"Deep analysis failed: {e}")
            
        return deep_data


# Global service instance
threat_analysis_service = ThreatAnalysisService()
