# GIB Website Download Pattern Analysis

## Overview
The GIB website (https://gib.re.kr) uses a JavaScript-based file download system with a two-step process.

## Download Process

### 1. JavaScript Function Call
Attachments are accessed via JavaScript function calls in this pattern:
```javascript
downloadAttFile('md_bbs', '1', '5653', '1')
```

Parameters:
- `attf_flag`: 'md_bbs' (module identifier)
- `seno`: '1' (board number) 
- `atnum`: '5653' (record number - same as rdno)
- `atpath`: '1' (attachment sequence number)

### 2. Download Endpoints

#### Step 1: Initial Download Request
- **URL**: `/lib/php/pub/download.php`
- **Method**: POST
- **Parameters**: 
  - `attf_flag=md_bbs`
  - `seno=1` 
  - `atpath=1`
  - `atnum=5653`
- **Response**: Returns HTML form that auto-submits to download_open.php

#### Step 2: Actual File Download
- **URL**: `/lib/php/pub/download_open.php`
- **Method**: POST (from auto-submitted form)
- **Parameters**: Same as step 1
- **Response**: File download with proper headers

## File Download Headers
```
Content-Disposition: inline; filename=붙임. 경북 산업용 헤프 이용자 고지.pdf
Content-Transfer-Encoding: binary
Content-Length: 103610
Content-Type: application/pdf
```

## HTML Structure

### Attachment Section
```html
<div class="div_attf_view_title">첨부파일</div>
<div class="div_attf_view_list">
    <div class="div_attf_view">
        <img src="/image/ico/clip2.gif" alt="첨부파일 아이콘">
        <span onclick="javascript:downloadAttFile('md_bbs', '1', '5653', '1');" 
              title="첨부파일 열기" 
              style="cursor:pointer; color:blue;">
            붙임. 경북 산업용 헴프 이용자 고지.pdf
        </span>
    </div>
</div>
```

### Key Form Fields
- `bdno`: Board number (1)
- `rdno`: Record number (5653) 
- `rdnoorg`: Original record number (5653)
- `mid`: Module ID (/news/notice)

## Implementation Notes

### For Scraper Implementation:
1. **Parse attachment links**: Look for `downloadAttFile()` function calls
2. **Extract parameters**: Parse the 4 parameters from function call
3. **Two-step download**: 
   - POST to `/lib/php/pub/download.php` first
   - Follow with POST to `/lib/php/pub/download_open.php`
4. **Required headers**:
   - `Content-Type: application/x-www-form-urlencoded`
   - `Referer: [detail page URL]`

### Filename Handling:
- Filenames in Content-Disposition header may have encoding issues
- Need to handle Korean characters properly
- Use EUC-KR or UTF-8 encoding as fallback

### Session Management:
- No special session handling required
- Standard HTTP requests work

## Test Results
- Successfully downloaded PDF file (103,610 bytes)
- File verified as valid PDF (4 pages)
- Pattern confirmed working for this post

## Example Implementation Pattern
```python
def download_attachment(self, attf_flag, seno, atnum, atpath, referer_url):
    # Step 1: Get download form
    response1 = self.session.post(
        f"{self.base_url}/lib/php/pub/download.php",
        data={
            'attf_flag': attf_flag,
            'seno': seno, 
            'atpath': atpath,
            'atnum': atnum
        },
        headers={'Referer': referer_url}
    )
    
    # Step 2: Actual download
    response2 = self.session.post(
        f"{self.base_url}/lib/php/pub/download_open.php", 
        data={
            'attf_flag': attf_flag,
            'seno': seno,
            'atpath': atpath, 
            'atnum': atnum
        },
        headers={'Referer': f"{self.base_url}/lib/php/pub/download.php"}
    )
    
    return response2
```