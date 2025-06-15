#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Voucher Enhanced 스크래퍼 3페이지 테스트
수정된 스크래퍼가 제대로 동작하는지 확인
"""

import os
import shutil
import sys
import time
from enhanced_export_voucher_scraper import EnhancedExportVoucherScraper

def test_enhanced_export_voucher():
    """Enhanced Export Voucher 스크래퍼 3페이지 테스트"""
    print("Enhanced Export Voucher 스크래퍼 3페이지 테스트")
    print("=" * 60)
    
    # 출력 디렉토리 설정
    output_dir = "output/export_voucher"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 스크래퍼 인스턴스 생성
    scraper = EnhancedExportVoucherScraper()
    
    try:
        # 3페이지 처리
        total_announcements = 0
        total_files = 0
        successful_downloads = 0
        announcements_with_files = 0
        
        for page in range(1, 4):  # 1, 2, 3페이지
            print(f"\n🔍 {page}페이지 처리 중...")
            
            # 목록 페이지 URL 생성
            list_url = scraper.get_list_url(page)
            print(f"📋 목록 URL: {list_url}")
            
            # 목록 페이지 가져오기
            try:
                response = scraper.session.get(list_url, verify=scraper.verify_ssl, timeout=10)
                if response.status_code != 200:
                    print(f"❌ 페이지 {page} 접근 실패: HTTP {response.status_code}")
                    continue
                    
                # 목록 파싱
                announcements = scraper.parse_list_page(response.text)
                print(f"📄 {len(announcements)}개 공고 발견")
                
                if not announcements:
                    print(f"⚠️  페이지 {page}에 공고가 없습니다.")
                    continue
                
                # 중복 검사
                new_announcements, early_stop = scraper.filter_new_announcements(announcements)
                print(f"🆕 신규 공고: {len(new_announcements)}개")
                
                if early_stop:
                    print("🔄 중복 임계값 도달 - 조기 종료")
                    break
                
                # 각 공고 처리
                page_files = 0
                page_downloads = 0
                page_announcements_with_files = 0
                
                for i, announcement in enumerate(new_announcements, 1):
                    total_announcements += 1
                    announcement_number = (page - 1) * 10 + i
                    
                    print(f"\n  📋 공고 {announcement_number}: {announcement['title'][:50]}...")
                    
                    # 상세 처리
                    try:
                        result = scraper.process_announcement(announcement, announcement_number, output_dir)
                        
                        if result:
                            attachments = result.get('attachments', [])
                            if attachments:
                                page_announcements_with_files += 1
                                page_files += len(attachments)
                                
                                for attachment in attachments:
                                    if attachment.get('download_success', False):
                                        page_downloads += 1
                                        # 파일 크기 확인
                                        local_path = attachment.get('local_path')
                                        if local_path and os.path.exists(local_path):
                                            file_size = os.path.getsize(local_path)
                                            print(f"    ✅ {attachment['name']} ({file_size:,} bytes)")
                                        else:
                                            print(f"    ⚠️  {attachment['name']} (파일 없음)")
                                    else:
                                        print(f"    ❌ {attachment['name']} (다운로드 실패)")
                            else:
                                print(f"    📎 첨부파일 없음")
                                
                            # 제목을 처리됨으로 추가
                            scraper.add_processed_title(announcement['title'])
                            
                        else:
                            print(f"    ❌ 처리 실패")
                    
                    except Exception as e:
                        print(f"    ❌ 처리 중 오류: {e}")
                    
                    # 과부하 방지
                    time.sleep(1)
                
                # 페이지 결과 요약
                print(f"\n📊 페이지 {page} 결과:")
                print(f"  - 처리된 공고: {len(new_announcements)}개")
                print(f"  - 첨부파일 있는 공고: {page_announcements_with_files}개")
                print(f"  - 총 첨부파일: {page_files}개")
                print(f"  - 다운로드 성공: {page_downloads}개")
                
                total_files += page_files
                successful_downloads += page_downloads
                announcements_with_files += page_announcements_with_files
                
            except Exception as e:
                print(f"❌ 페이지 {page} 처리 중 오류: {e}")
        
        # 처리된 제목 저장
        scraper.save_processed_titles()
        
        # 최종 결과 요약
        print(f"\n" + "=" * 60)
        print(f"🎯 최종 결과 요약:")
        print(f"  - 총 처리 공고: {total_announcements}개")
        print(f"  - 첨부파일 있는 공고: {announcements_with_files}개")
        print(f"  - 총 첨부파일: {total_files}개")
        print(f"  - 다운로드 성공: {successful_downloads}개")
        
        if total_files > 0:
            success_rate = (successful_downloads / total_files) * 100
            print(f"  - 다운로드 성공률: {success_rate:.1f}%")
        else:
            print(f"  - 다운로드 성공률: N/A (첨부파일 없음)")
        
        print(f"  - 출력 디렉토리: {output_dir}")
        
        # 성공 여부 판단
        if successful_downloads > 0:
            print(f"\n🎉 테스트 성공! {successful_downloads}개 파일 다운로드 완료")
            return True
        elif total_files == 0:
            print(f"\n✅ 테스트 완료 (첨부파일이 있는 공고 없음)")
            return True
        else:
            print(f"\n❌ 테스트 실패 (파일 다운로드 실패)")
            return False
    
    except Exception as e:
        print(f"\n❌ 전체 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_export_voucher()
    if success:
        print("\n✅ Export Voucher Enhanced 테스트 완료!")
        sys.exit(0)
    else:
        print("\n💥 Export Voucher Enhanced 테스트 실패!")
        sys.exit(1)