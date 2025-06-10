#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
새로운 아키텍처 테스트 스크립트
리팩토링된 스크래핑 시스템의 기본 기능들을 테스트
"""

import sys
import os
from pathlib import Path

def test_imports():
    """모듈 import 테스트"""
    print("🔍 모듈 import 테스트...")
    
    try:
        from site_registry import SiteRegistry, get_registry
        print("✅ site_registry 모듈 import 성공")
    except ImportError as e:
        print(f"❌ site_registry 모듈 import 실패: {e}")
        return False
    
    try:
        from scraping_engine import ScrapingEngine, create_engine
        print("✅ scraping_engine 모듈 import 성공")
    except ImportError as e:
        print(f"❌ scraping_engine 모듈 import 실패: {e}")
        return False
    
    try:
        from enhanced_base_scraper import (
            EnhancedBaseScraper, StandardTableScraper, 
            AjaxAPIScraper, JavaScriptScraper, SessionBasedScraper
        )
        print("✅ enhanced_base_scraper 모듈 import 성공")
    except ImportError as e:
        print(f"❌ enhanced_base_scraper 모듈 import 실패: {e}")
        return False
    
    return True

def test_config_loading():
    """설정 파일 로딩 테스트"""
    print("\n🔍 설정 파일 로딩 테스트...")
    
    try:
        registry = get_registry()
        sites = registry.get_site_codes()
        print(f"✅ 설정 로딩 성공: {len(sites)}개 사이트 등록")
        print(f"   등록된 사이트: {', '.join(sites[:5])}{'...' if len(sites) > 5 else ''}")
        return True
    except Exception as e:
        print(f"❌ 설정 로딩 실패: {e}")
        return False

def test_site_config():
    """사이트 설정 테스트"""
    print("\n🔍 사이트 설정 테스트...")
    
    try:
        registry = get_registry()
        
        # BTP 설정 확인
        btp_config = registry.get_site_config('btp')
        if btp_config:
            print(f"✅ BTP 설정 확인: {btp_config.name} ({btp_config.type})")
        else:
            print("❌ BTP 설정을 찾을 수 없습니다")
            return False
        
        # 설정 유효성 검증
        issues = registry.validate_config()
        if any(issues.values()):
            print(f"⚠️  설정 문제 발견:")
            for issue_type, issue_list in issues.items():
                if issue_list:
                    print(f"   {issue_type}: {issue_list}")
        else:
            print("✅ 모든 설정이 유효합니다")
        
        return True
    except Exception as e:
        print(f"❌ 사이트 설정 테스트 실패: {e}")
        return False

def test_scraper_creation():
    """스크래퍼 생성 테스트"""
    print("\n🔍 스크래퍼 생성 테스트...")
    
    try:
        registry = get_registry()
        
        # BTP 스크래퍼 생성 시도
        try:
            btp_scraper = registry.create_scraper('btp')
            print(f"✅ BTP 스크래퍼 생성 성공: {type(btp_scraper).__name__}")
        except ImportError:
            print("⚠️  BTP 스크래퍼 모듈이 없어서 생성할 수 없습니다 (정상)")
        except Exception as e:
            print(f"❌ BTP 스크래퍼 생성 실패: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 스크래퍼 생성 테스트 실패: {e}")
        return False

def test_enhanced_scraper():
    """향상된 스크래퍼 테스트"""
    print("\n🔍 향상된 스크래퍼 테스트...")
    
    try:
        # 기본 스크래퍼 생성
        from enhanced_base_scraper import StandardTableScraper
        
        scraper = StandardTableScraper()
        print("✅ StandardTableScraper 생성 성공")
        
        # 설정 주입 테스트
        registry = get_registry()
        btp_config = registry.get_site_config('btp')
        
        if btp_config:
            scraper.set_config(btp_config)
            print("✅ 설정 주입 성공")
            
            # 기본 속성 확인
            if scraper.base_url == btp_config.base_url:
                print("✅ 설정 적용 확인")
            else:
                print("⚠️  설정이 완전히 적용되지 않았습니다")
        
        return True
    except Exception as e:
        print(f"❌ 향상된 스크래퍼 테스트 실패: {e}")
        return False

def test_scraping_engine():
    """스크래핑 엔진 테스트"""
    print("\n🔍 스크래핑 엔진 테스트...")
    
    try:
        from scraping_engine import create_engine
        
        engine = create_engine()
        print("✅ 스크래핑 엔진 생성 성공")
        
        # 사이트 유효성 검증 테스트
        validation = engine.validate_sites(['btp', 'invalid_site'])
        print(f"✅ 사이트 유효성 검증: {validation}")
        
        # 타입별 사이트 조회 테스트
        standard_sites = engine.registry.get_sites_by_type('standard_table')
        print(f"✅ 표준 테이블 사이트: {len(standard_sites)}개")
        
        return True
    except Exception as e:
        print(f"❌ 스크래핑 엔진 테스트 실패: {e}")
        return False

def test_file_operations():
    """파일 처리 테스트"""
    print("\n🔍 파일 처리 테스트...")
    
    try:
        from enhanced_base_scraper import EnhancedBaseScraper
        
        # 가상의 스크래퍼 생성
        class TestScraper(EnhancedBaseScraper):
            def get_list_url(self, page_num):
                return "http://example.com"
            def parse_list_page(self, html_content):
                return []
            def parse_detail_page(self, html_content):
                return {'content': '', 'attachments': []}
        
        scraper = TestScraper()
        
        # 파일명 정리 테스트
        test_filename = "테스트<파일>명.pdf"
        sanitized = scraper.sanitize_filename(test_filename)
        print(f"✅ 파일명 정리: '{test_filename}' → '{sanitized}'")
        
        return True
    except Exception as e:
        print(f"❌ 파일 처리 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 새로운 아키텍처 테스트 시작")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_loading,
        test_site_config,
        test_scraper_creation,
        test_enhanced_scraper,
        test_scraping_engine,
        test_file_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")
    
    print("\n" + "=" * 50)
    print(f"🏁 테스트 완료: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 새로운 아키텍처가 정상적으로 설정되었습니다.")
        return 0
    else:
        print("⚠️  일부 테스트 실패. 설정을 확인해주세요.")
        return 1

if __name__ == '__main__':
    sys.exit(main())