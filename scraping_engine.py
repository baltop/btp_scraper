# -*- coding: utf-8 -*-
"""
스크래핑 엔진 - 통합된 스크래핑 실행 관리자
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from site_registry import SiteRegistry, get_registry

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraping.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class ScrapingEngine:
    """통합 스크래핑 엔진"""
    
    def __init__(self, registry: Optional[SiteRegistry] = None):
        self.registry = registry or get_registry()
        self.results: Dict[str, Dict[str, Any]] = {}
        self.continue_on_error = True
        
    def scrape_site(self, site_code: str, max_pages: int = None, output_dir: str = None) -> Dict[str, Any]:
        """단일 사이트 스크래핑"""
        logger.info(f"사이트 스크래핑 시작: {site_code}")
        
        # 설정 가져오기
        config = self.registry.get_site_config(site_code)
        if not config:
            raise ValueError(f"알 수 없는 사이트: {site_code}")
        
        # 기본값 설정
        if max_pages is None:
            max_pages = self.registry.get_default('max_pages', 4)
        
        if output_dir is None:
            base_output = self.registry.get_default('output_dir', 'output')
            output_dir = os.path.join(base_output, site_code)
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        result = {
            'site_code': site_code,
            'site_name': config.name,
            'status': 'started',
            'pages_processed': 0,
            'announcements_processed': 0,
            'errors': [],
            'output_dir': output_dir,
            'start_time': time.time()
        }
        
        try:
            # 스크래퍼 생성
            scraper = self.registry.create_scraper(site_code)
            
            # SSL 설정 적용
            if hasattr(scraper, 'verify_ssl'):
                scraper.verify_ssl = config.ssl_verify
            
            # 인코딩 설정 적용
            if hasattr(scraper, 'default_encoding') and config.encoding != 'auto':
                scraper.default_encoding = config.encoding
            
            logger.info(f"{config.name} 스크래핑 시작 - 최대 {max_pages}페이지")
            
            # 스크래핑 실행
            if hasattr(scraper, 'scrape_pages'):
                # 기존 방식과 호환
                scraper.scrape_pages(max_pages=max_pages, output_base=output_dir)
            else:
                # 새로운 방식 (향후 구현)
                self._run_custom_scraping(scraper, config, max_pages, output_dir)
            
            result['status'] = 'completed'
            result['pages_processed'] = max_pages  # 실제 처리된 페이지 수로 업데이트 필요
            
            logger.info(f"{config.name} 스크래핑 완료")
            
        except KeyboardInterrupt:
            result['status'] = 'interrupted'
            logger.info(f"{config.name} 스크래핑이 사용자에 의해 중단됨")
            raise
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"{config.name} 스크래핑 실패: {e}")
            
            if not self.continue_on_error:
                raise
        
        finally:
            result['end_time'] = time.time()
            result['duration'] = result.get('end_time', time.time()) - result['start_time']
            self.results[site_code] = result
        
        return result
    
    def scrape_sites(self, site_codes: List[str], max_pages: int = None, output_base: str = None) -> Dict[str, Dict[str, Any]]:
        """여러 사이트 순차 스크래핑"""
        logger.info(f"다중 사이트 스크래핑 시작: {', '.join(site_codes)}")
        
        results = {}
        
        for site_code in site_codes:
            if site_code not in self.registry.get_site_codes():
                logger.warning(f"알 수 없는 사이트 건너뛰기: {site_code}")
                continue
            
            try:
                # 출력 디렉토리 설정
                output_dir = None
                if output_base:
                    output_dir = os.path.join(output_base, site_code)
                
                # 사이트 스크래핑
                result = self.scrape_site(site_code, max_pages, output_dir)
                results[site_code] = result
                
                # 사이트 간 대기
                delay = self.registry.get_default('delay_between_sites', 3)
                if delay > 0 and site_code != site_codes[-1]:  # 마지막 사이트가 아니면
                    logger.info(f"다음 사이트 처리 전 {delay}초 대기")
                    time.sleep(delay)
                
            except KeyboardInterrupt:
                logger.info("사용자에 의해 전체 스크래핑이 중단됨")
                break
            except Exception as e:
                logger.error(f"{site_code} 스크래핑 실패, 다음 사이트로 계속: {e}")
                if not self.continue_on_error:
                    break
        
        logger.info(f"다중 사이트 스크래핑 완료: {len(results)}/{len(site_codes)} 성공")
        return results
    
    def scrape_all(self, max_pages: int = None, output_base: str = None, exclude: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """모든 등록된 사이트 스크래핑"""
        all_sites = self.registry.get_site_codes()
        
        if exclude:
            all_sites = [site for site in all_sites if site not in exclude]
        
        logger.info(f"전체 사이트 스크래핑 시작: {len(all_sites)}개 사이트")
        return self.scrape_sites(all_sites, max_pages, output_base)
    
    def scrape_by_type(self, scraper_type: str, max_pages: int = None, output_base: str = None) -> Dict[str, Dict[str, Any]]:
        """특정 타입의 사이트들만 스크래핑"""
        sites = self.registry.get_sites_by_type(scraper_type)
        
        if not sites:
            logger.warning(f"타입 '{scraper_type}'에 해당하는 사이트가 없습니다")
            return {}
        
        logger.info(f"타입별 스크래핑 시작 ({scraper_type}): {', '.join(sites)}")
        return self.scrape_sites(sites, max_pages, output_base)
    
    def _run_custom_scraping(self, scraper, config, max_pages: int, output_dir: str):
        """사용자 정의 스크래핑 로직 (향후 확장용)"""
        # 현재는 기존 방식 사용
        if hasattr(scraper, 'scrape_pages'):
            scraper.scrape_pages(max_pages=max_pages, output_base=output_dir)
        else:
            raise NotImplementedError(f"스크래퍼 {type(scraper).__name__}는 scrape_pages 메서드가 없습니다")
    
    def get_results(self) -> Dict[str, Dict[str, Any]]:
        """스크래핑 결과 반환"""
        return self.results.copy()
    
    def print_summary(self):
        """결과 요약 출력"""
        if not self.results:
            print("스크래핑 결과가 없습니다.")
            return
        
        print("\n" + "="*60)
        print("스크래핑 결과 요약")
        print("="*60)
        
        total_sites = len(self.results)
        successful = sum(1 for r in self.results.values() if r['status'] == 'completed')
        failed = sum(1 for r in self.results.values() if r['status'] == 'failed')
        interrupted = sum(1 for r in self.results.values() if r['status'] == 'interrupted')
        
        print(f"전체 사이트: {total_sites}")
        print(f"성공: {successful}")
        print(f"실패: {failed}")
        print(f"중단: {interrupted}")
        print()
        
        for site_code, result in self.results.items():
            status_icon = {
                'completed': '✓',
                'failed': '✗',
                'interrupted': '⚠'
            }.get(result['status'], '?')
            
            duration = result.get('duration', 0)
            print(f"{status_icon} {result['site_name']} ({site_code})")
            print(f"   상태: {result['status']}")
            print(f"   소요시간: {duration:.1f}초")
            print(f"   출력위치: {result['output_dir']}")
            
            if result['errors']:
                print(f"   오류: {result['errors'][0]}")
            print()
        
        print("="*60)
    
    def set_continue_on_error(self, continue_on_error: bool):
        """오류 발생 시 계속 진행 여부 설정"""
        self.continue_on_error = continue_on_error
    
    def validate_sites(self, site_codes: List[str]) -> Dict[str, List[str]]:
        """사이트 코드 유효성 검증"""
        valid_sites = self.registry.get_site_codes()
        
        valid = [site for site in site_codes if site in valid_sites]
        invalid = [site for site in site_codes if site not in valid_sites]
        
        return {
            'valid': valid,
            'invalid': invalid
        }


def create_engine(config_file: str = "sites_config.yaml") -> ScrapingEngine:
    """스크래핑 엔진 생성"""
    registry = get_registry(config_file)
    return ScrapingEngine(registry)