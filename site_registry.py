# -*- coding: utf-8 -*-
"""
사이트 레지스트리 - 설정 기반 스크래퍼 관리 시스템
"""

import yaml
import importlib
import logging
from typing import Dict, List, Optional, Type, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SiteConfig:
    """개별 사이트 설정 클래스"""
    
    def __init__(self, site_code: str, config_data: Dict[str, Any]):
        self.site_code = site_code
        self.name = config_data.get('name', site_code)
        self.scraper_class = config_data.get('scraper_class')
        self.scraper_module = config_data.get('scraper_module')
        self.base_url = config_data.get('base_url')
        self.list_url = config_data.get('list_url')
        self.api_url = config_data.get('api_url')
        self.type = config_data.get('type', 'standard_table')
        self.encoding = config_data.get('encoding', 'auto')
        self.ssl_verify = config_data.get('ssl_verify', True)
        self.pagination = config_data.get('pagination', {})
        self.selectors = config_data.get('selectors', {})
        self.api_config = config_data.get('api_config', {})
        self._raw_config = config_data
    
    def get(self, key: str, default=None):
        """설정 값 가져오기"""
        return self._raw_config.get(key, default)
    
    def __repr__(self):
        return f"SiteConfig(site_code='{self.site_code}', name='{self.name}', type='{self.type}')"


class SiteRegistry:
    """사이트 레지스트리 - 설정 기반 스크래퍼 관리"""
    
    def __init__(self, config_file: str = "sites_config.yaml"):
        self.config_file = config_file
        self.sites: Dict[str, SiteConfig] = {}
        self.defaults: Dict[str, Any] = {}
        self.scraper_types: Dict[str, Dict[str, str]] = {}
        self._scraper_classes: Dict[str, Type] = {}
        self.load_config()
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                logger.error(f"설정 파일을 찾을 수 없습니다: {self.config_file}")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 기본 설정 로드
            self.defaults = config.get('defaults', {})
            self.scraper_types = config.get('scraper_types', {})
            
            # 사이트 설정 로드
            sites_config = config.get('sites', {})
            for site_code, site_data in sites_config.items():
                self.sites[site_code] = SiteConfig(site_code, site_data)
            
            logger.info(f"설정 로드 완료: {len(self.sites)}개 사이트")
            
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise
    
    def get_site_config(self, site_code: str) -> Optional[SiteConfig]:
        """사이트 설정 가져오기"""
        return self.sites.get(site_code)
    
    def get_site_codes(self) -> List[str]:
        """등록된 모든 사이트 코드 목록"""
        return list(self.sites.keys())
    
    def get_sites_by_type(self, scraper_type: str) -> List[str]:
        """특정 타입의 사이트들 반환"""
        return [
            site_code for site_code, config in self.sites.items()
            if config.type == scraper_type
        ]
    
    def _load_scraper_class(self, config: SiteConfig) -> Type:
        """스크래퍼 클래스 동적 로드"""
        cache_key = f"{config.scraper_module}.{config.scraper_class}"
        
        if cache_key in self._scraper_classes:
            return self._scraper_classes[cache_key]
        
        try:
            # 모듈 import
            module = importlib.import_module(config.scraper_module)
            
            # 클래스 가져오기
            scraper_class = getattr(module, config.scraper_class)
            
            # 캐시에 저장
            self._scraper_classes[cache_key] = scraper_class
            
            logger.debug(f"스크래퍼 클래스 로드: {cache_key}")
            return scraper_class
            
        except (ImportError, AttributeError) as e:
            logger.error(f"스크래퍼 클래스 로드 실패 {cache_key}: {e}")
            raise
    
    def create_scraper(self, site_code: str):
        """스크래퍼 인스턴스 생성"""
        config = self.get_site_config(site_code)
        if not config:
            raise ValueError(f"알 수 없는 사이트: {site_code}")
        
        try:
            scraper_class = self._load_scraper_class(config)
            scraper = scraper_class()
            
            # 설정 주입 (스크래퍼가 config를 받을 수 있다면)
            if hasattr(scraper, 'set_config'):
                scraper.set_config(config)
            
            logger.debug(f"스크래퍼 생성 완료: {site_code}")
            return scraper
            
        except Exception as e:
            logger.error(f"스크래퍼 생성 실패 {site_code}: {e}")
            raise
    
    def validate_config(self) -> Dict[str, List[str]]:
        """설정 검증"""
        issues = {
            'missing_fields': [],
            'invalid_modules': [],
            'invalid_classes': []
        }
        
        for site_code, config in self.sites.items():
            # 필수 필드 확인
            required_fields = ['name', 'scraper_class', 'scraper_module', 'base_url', 'list_url']
            for field in required_fields:
                if not getattr(config, field):
                    issues['missing_fields'].append(f"{site_code}.{field}")
            
            # 모듈과 클래스 유효성 확인
            try:
                self._load_scraper_class(config)
            except ImportError:
                issues['invalid_modules'].append(f"{site_code}: {config.scraper_module}")
            except AttributeError:
                issues['invalid_classes'].append(f"{site_code}: {config.scraper_class}")
        
        return issues
    
    def get_default(self, key: str, default=None):
        """기본 설정값 가져오기"""
        return self.defaults.get(key, default)
    
    def add_site(self, site_code: str, config_data: Dict[str, Any]):
        """런타임에 사이트 추가"""
        self.sites[site_code] = SiteConfig(site_code, config_data)
        logger.info(f"사이트 추가: {site_code}")
    
    def remove_site(self, site_code: str):
        """사이트 제거"""
        if site_code in self.sites:
            del self.sites[site_code]
            logger.info(f"사이트 제거: {site_code}")
    
    def __repr__(self):
        return f"SiteRegistry(sites={len(self.sites)}, config_file='{self.config_file}')"


# 전역 레지스트리 인스턴스
_global_registry = None

def get_registry(config_file: str = "sites_config.yaml") -> SiteRegistry:
    """전역 레지스트리 인스턴스 가져오기"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SiteRegistry(config_file)
    return _global_registry

def reload_registry(config_file: str = "sites_config.yaml") -> SiteRegistry:
    """레지스트리 다시 로드"""
    global _global_registry
    _global_registry = SiteRegistry(config_file)
    return _global_registry