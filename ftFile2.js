(function () {

    if (window.ftFile2Loaded) {
        return;
    }

    window.File2JS = {
        maxIndex: 0,
        fileUploadInfo: [],
        addFileForm : function(selector, inputName, comment, docId){
            $.ajax({
                "url" :"/common/File2UploadForm",
                "type" : "get",
                "traditional" : true,
                "data" :{
                    inputName : inputName,
                    comment : comment||'첨부파일의 용량은 1개당 50MB로 제한되며, 복수의 파일을 첨부할 수 있습니다',
                    docId : docId
                },
                "contentType" : "text/plain;charset=utf-8",
                "success" : function(html){
                    var $fileObj = $($.trim(html));
                    initFormEvent($fileObj.find('[data-file-container]'));
                    $(selector).append($fileObj);
                }
            });
        },
        addFileImageForm : function(selector, inputName, comment, docId){
            $.ajax({
                "url" :"/common/File2ImageUploadForm",
                "type" : "get",
                "traditional" : true,
                "data" :{
                    inputName : inputName,
                    comment : comment||'첨부파일의 용량은 1개당 50MB로 제한되며, 이미지 4개 이상은 노출 되지 않습니다.',
                    docId : docId
                },
                "contentType" : "text/plain;charset=utf-8",
                "success" : function(html){
                    var $fileObj = $($.trim(html));
                    initFormEvent($fileObj.find('[data-file-container]'));
                    $(selector).append($fileObj);
                }
            });
        },
        addDownForm : function(selector, docId){
            $.ajax({
                "url" :"/common/File2DownloadList",
                "type" : "get",
                "traditional" : true,
                "data" :{
                    docId : docId
                },
                "contentType" : "text/plain;charset=utf-8",
                "success" : function(html){
                    var $fileObj = $($.trim(html));
                    $(selector).append($fileObj);
                    initListEvent($fileObj.find('[data-file-download]'));
                }
            });
        },
        getFileCount : function(selector) {
            var fileCnt = 0;
            $(selector).find('[data-file-container]').find("[data-file-item]").each(function(){
                if($(this).find("[data-file-uploading]").length==0){
                    fileCnt++;
                }
            });
            return fileCnt;
        },
        chkFileNecess : function(inputName) {
            return $('[data-file-container][data-input-name='+inputName+']').find("[data-file-item]").length
        },
        loadFileList : function(obj){
            $(obj).find('[data-file-download]').each(function(){
                console.log(this);
                initListEvent(this);
            });
        },
        loadFileAllList : function(obj){
            $(obj).find('[data-file-all-download]').each(function(){
                console.log(this);
                initAllListEvent(this);
            });
        },
        removeFileForm : function(selector){
        	var index = $(selector).find('[data-file-container]').attr("data-file-container");
        	$("body > form[name=ftFileForm_"+index+"]").remove();
        	$(selector).find('[data-file-container]').parent().remove();
        },
        hasUploadComplete : function(selector){
        	var $sel = $(selector || 'body');
        	return $sel.find("[data-file-uploading]").length == 0;
        }
    };

    function fnFileExt(fileName) {
        if (fileName == '') {
            return '';
        }

        var start = fileName.lastIndexOf(".");
        var ext = '';
        if (start > -1) {
            ext = fileName.substring(start + 1).toLowerCase();
        }
        return ext;
    }

    var imageType = new Array('bmp', 'png', 'jpg', 'jpeg', 'gif');

    function fnFileImg(fileName) {
        var fileGif = new Array('bmp', 'doc', 'etc', 'exe', 'gif', 'gul', 'htm', 'html', 'hwp', 'ini', 'jpg', 'mgr', 'mpg', 'pdf', 'ppt', 'print', 'tif', 'txt', 'wav', 'xls', 'xml', 'zip');
        if (fileName == '') {
            return '';
        }
        var name = fnFileExt(fileName);
        var retFlag = false;
        for (var fileInx = 0; fileInx < fileGif.length; fileInx++) {
            if (name == fileGif[fileInx]) {
                retFlag = true;
                break;
            }
        }
        var retStr = '';
        if (retFlag) {
            retStr = '<img style="vertical-align: middle" src="/static/images/ftSystem/attach_' + name + '.gif" alt="" border="0">';
        } else {
            retStr = '<img style="vertical-align: middle" src="/static/images/ftSystem/icon_doc.gif" alt="" border="0">';
        }
        return retStr;
    }

    function addFileDownLoadItem(index, item) {
        var imgTag = fnFileImg(item.fileName);
        var $fileItem = $("<div data-file-item='" + item.fileId + "' data-sec-code='"+item.secCode+"'><input class='file-checkbox' type='checkbox' title='파일선택'/>" +
            "<a class='file-filename' href='/common.FileDownload.do?file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
            "<span class='file-filesize'>" + getFileSizeStr(item.fileSize) + "</span>" +
            "</div>");
        $('[data-file-download=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addFileDownLoadItem2(index, item) {
        var imgTag = fnFileImg(item.fileName);
        var $fileItem = $("<div data-file-item='" + item.fileId + "' data-sec-code='"+item.secCode+"'><input class='file-checkbox' type='checkbox' title='파일선택'/>" +
            "<a class='file-filename' href='/common.FileDownloadMobile.do?type=2&file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
            "<span class='file-filesize'>" + getFileSizeStr(item.fileSize) + "</span>" +
            "</div>");
        $('[data-file-download-mobile=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addFileImageItem(index, item) {
        var $fileItem = $("<div class='file2-image' data-file-item='"+item.fileId+"'>" +
            "<img class='file2-thumbnail' data-file-name='"+item.fileName+"' src='/common/File2Image/"+item.fileId+"/S/122x84.jpg?secCode="+item.secCode+"' alt='"+item.fileName+"'/>" +
            "</div>");
        $('[data-file-download=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addFileDownLoadAllItem(index, item) {
        var imgTag = fnFileImg(item.fileName);
        var $fileItem = "";
        if(item.delYn === 'Y'){
            $fileItem = $("<div data-file-item='" + item.fileId + "' data-sec-code='"+item.secCode+"' data-del-yn='Y'><input class='file-checkbox' type='checkbox' title='파일선택'/>" +
                "<a class='file-filename' href='/common.FileDownload.do?del_yn=ALL&file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
                "<span class='file-filesize'>" + getFileSizeStr(item.fileSize) + "</span>" +
                "</div>");
        }else{
            $fileItem = $("<div data-file-item='" + item.fileId + "' data-sec-code='"+item.secCode+"'><input class='file-checkbox' type='checkbox' title='파일선택'/>" +
                "<a class='file-filename' href='/common.FileDownload.do?del_yn=ALL&file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
                "<span class='file-filesize'>" + getFileSizeStr(item.fileSize) + "</span>" +
                "</div>");
        }

        $('[data-file-all-download=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addFileImageAllItem(index, item) {
        var $fileItem = $("<div class='file2-image' data-file-item='"+item.fileId+"'>" +
            "<img class='file2-thumbnail' data-file-name='"+item.fileName+"' src='/common/File2Image/"+item.fileId+"/S/122x84.jpg?secCode="+item.secCode+"' alt='"+item.fileName+"'/>" +
            "</div>");
        $('[data-file-all-download=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addFileItem(index, item) {
        var imgTag = fnFileImg(item.fileName);
        var $fileItem = $("<div data-file-item='" + item.fileId + "'><input class='file-checkbox' type='checkbox' title='파일선택'/>" +
            // "<span class='file-filename' data-file-name='"+item.fileName+"'>" + imgTag + item.fileName + "</span>" +
            // "<a class='file-filename' href='/common.FileDownload.do?file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
            "<a class='file-filename' data-file-name='"+item.fileName+"' href='/common.FileDownload.do?file_id="+item.fileId+"&sec_code="+item.secCode+"'>" + imgTag + item.fileName + "</a>" +
            "<span class='file-filesize'>" + getFileSizeStr(item.fileSize) + "</span>" +
            "</div>");
        $('[data-file-container=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function addImageFileItem(index, item) {
        var $fileItem = $("<div class='file2-image' data-file-item='"+item.fileId+"'>" +
            "<img class='file2-thumbnail' data-file-name='"+item.fileName+"' src='/common/File2Image/"+item.fileId+"/S/122x84.jpg?secCode="+item.secCode+"' alt='"+item.fileName+"'/>" +
            "<input class='file2-thumbnail-cb' class='file-checkbox' type='checkbox' title='파일선택'/>" +
            "</div>");
        $('[data-file-container=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function uploadFileItem(index, fileName) {
        var imgTag = fnFileImg(fileName);
        var $fileItem = $("<div data-file-item><input class='file-checkbox' type='checkbox' disabled='disabled'  title='파일선택'/>" +
            "<span class='file-filename' data-file-name='"+fileName+"'>" + imgTag + fileName + "</span>" +
            "<span class='file-filesize' data-file-uploading='" + fileName + "'><img style='height:10px; width:10px;' src='/static/images/ftSystem/ajaxSpinner.gif' alt='loading'/></span>" +
            "</div>");
        $('[data-file-container=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function uploadImageFileItem(index, fileName) {
        var $fileItem = $("<div class='file2-image' data-file-item>" +
            "<img class='file2-thumbnail' data-file-name='"+fileName+"' data-file-uploading='"+fileName+"' src='/static/images/ftSystem/ajaxSpinner.gif' alt='loading'/>" +
            "<input class='file2-thumbnail-cb' class='file-checkbox' type='checkbox' disabled='disabled' title='파일선택'/>" +
            "</div>");
        $('[data-file-container=' + index + ']').find("[data-file-list]").append($fileItem);
    }

    function removeFileItem(index, fileName) {
        $('[data-file-container=' + index + ']').find("[data-file-item]").each(function () {
            if ($.trim($(this).find('[data-file-name]').attr('data-file-name')) === fileName) {
                var fileId = $(this).attr('data-file-item');
                if (!File2JS.fileUploadInfo[index]) {
                    File2JS.fileUploadInfo[index] = [];
                }
                if (fileId !== '') {
                    var item = {
                        mode: 'delete',
                        fileId: fileId
                    }
                    File2JS.fileUploadInfo[index].push(item);
                } else {
                    for (var i = 0; i < File2JS.fileUploadInfo[index].length; i++) {
                        if (File2JS.fileUploadInfo[index][i].fileName === fileName) {
                            File2JS.fileUploadInfo[index].splice(i, 1);
                        }
                    }
                }
                $(this).remove();
            }
        });
        setJsonString(index);
    }

    function getFileSizeStr(fileSize) {
        var size = parseInt(fileSize, 10);
        if (size / 1024 / 1024 / 1024 > 1) {
            return Math.round(size / 1024 / 1024 / 1024 * 100) / 100 + ' GB';
        } else if (size / 1024 / 1024 > 1) {
            return Math.round(size / 1024 / 1024 * 100) / 100 + ' MB';
        } else if (size / 1024 > 1) {
            return Math.round(size / 1024 * 100) / 100 + ' KB';
        } else {
            return Math.round(size * 100) / 100 + 'B';
        }
    }

    function completeFileItem(index, item) {
        $('[data-file-container=' + index + ']').find("[data-file-uploading='" + item.fileName + "']").each(function () {
            $(this).removeAttr('data-file-uploading');
            $(this).text(getFileSizeStr(item.fileSize));
            $(this).closest('[data-file-item]').find("input[type=checkbox]").removeAttr('disabled');
            if (File2JS.fileUploadInfo[index] === undefined) {
                File2JS.fileUploadInfo[index] = []
            }
            item.mode = 'new';
            File2JS.fileUploadInfo[index].push(item);
        });
        setJsonString(index);
    }

    function completeImageFileItem(index, item) {
        $('[data-file-container=' + index + ']').find("[data-file-uploading='" + item.fileName + "']").each(function () {
            $(this).removeAttr('data-file-uploading');
            $(this).closest('[data-file-item]').find("input[type=checkbox]").removeAttr('disabled');
            if (File2JS.fileUploadInfo[index] === undefined) {
                File2JS.fileUploadInfo[index] = []
            }
            $(this).attr("src", "/common/File2Image/tmp/S/122x84.jpg?storePath="+encodeURIComponent(item.storePath)+"&fileName="+encodeURIComponent(item.fileName));
            $(this).attr("alt", item.fileName);
            item.mode = 'new';
            File2JS.fileUploadInfo[index].push(item);
        });
        setJsonString(index);
    }

    function setJsonString(index) {
        var slct = $('[data-file-container=' + index + ']').attr("data-input-name") + "Json";
        $('[data-file-container=' + index + ']').parent().find('input[name=\"'+slct+'\"]').val(JSON.stringify(File2JS.fileUploadInfo[index]));
    }

    function initFormEvent(obj){
        var index = File2JS.maxIndex++;
        var docId = $(obj).attr('data-doc-id')||'';
        $(obj).attr('data-file-container', index);
        var $this = $(obj);
        var fType =  $(obj).attr('data-form-type');
        // 최초 데이터 로드
        if (docId !== '') {
            $.ajax({
                url: "/common/File2List",
                type: "GET",
                cache: false,
                traditional : true,
                data:{
                    docId:docId
                },
                success: function (data) {
                    for (var i = 0; i < data.length; i++) {
                        if("image" == fType){
                            addImageFileItem(index, data[i]);
                        } else {
                            addFileItem(index, data[i]);
                        }

                    }
                    $this.find('[data-loading-icon]').remove();
                    $this.find('[data-button-group]').show(0);
                }
            });
        } else {
            $this.find('[data-loading-icon]').remove();
            $this.find('[data-button-group]').show(0);
        }

        $('body').append("<form name='ftFileForm_"+index+"' method='post' enctype='multipart/form-data' style='width:0px; height:0px; border:0px; display:block; visibility:hidden;'>" +
            "<input type='hidden' name='docId' value='"+docId+"'/></form>");
    }

    function initListEvent(obj){
        var index = File2JS.maxIndex++;
        var docId = $(obj).attr('data-doc-id');
        $(obj).attr('data-file-download', index);
        var fType = $(obj).attr('data-form-type');
        var $this = $(obj);
        // 최초 데이터 로드
        if (docId !== '') {
            $.ajax({
                url: "/common/File2List",
                type: "GET",
                cache: false,
                traditional : true,
                data:{
                    docId:docId
                },
                success: function (data) {
                    if(data.length === 0){
                        $this.find('[data-loading-icon]').remove();
                        return;
                    }
                    for (var i = 0; i < data.length; i++) {
                        if(fType == 'image'){
                            addFileImageItem(index, data[i]);
                        } else {
                            addFileDownLoadItem(index, data[i]);
                        }
                    }
                    $this.find('[data-loading-icon]').remove();
                    if(data.length === 1){
                        $this.find('.file-checkbox').hide(0);
                    } else{
                        $this.find('[data-button-group]').show(0);
                    }
                }
            });
        } else {
            $this.find('[data-loading-icon]').remove();
        }
    }

    function initListEvent(obj){
        var index = File2JS.maxIndex++;
        var docId = $(obj).attr('data-doc-id');
        $(obj).attr('data-file-download', index);
        var fType = $(obj).attr('data-form-type');
        var $this = $(obj);
        // 최초 데이터 로드
        if (docId !== '') {
            $.ajax({
                url: "/common/File2List",
                type: "GET",
                cache: false,
                traditional : true,
                data:{
                    docId:docId
                },
                success: function (data) {
                    if(data.length === 0){
                        $this.find('[data-loading-icon]').remove();
                        return;
                    }
                    for (var i = 0; i < data.length; i++) {
                        if(fType == 'image'){
                            addFileImageItem(index, data[i]);
                        } else {
                            addFileDownLoadItem(index, data[i]);
                        }
                    }
                    $this.find('[data-loading-icon]').remove();
                    if(data.length === 1){
                        $this.find('.file-checkbox').hide(0);
                    } else{
                        $this.find('[data-button-group]').show(0);
                    }
                }
            });
        } else {
            $this.find('[data-loading-icon]').remove();
        }
    }

    function initAllListEvent(obj){
        var index = File2JS.maxIndex++;
        var docId = $(obj).attr('data-doc-id');
        $(obj).attr('data-file-all-download', index);
        var fType = $(obj).attr('data-form-type');
        var $this = $(obj);
        // 최초 데이터 로드
        if (docId !== '') {
            $.ajax({
                url: "/common/File2AllList",
                type: "GET",
                cache: false,
                traditional : true,
                data:{
                    docId:docId,
                    delYn:"ALL"
                },
                success: function (data) {
                    if(data.length === 0){
                        $this.find('[data-loading-icon]').remove();
                        return;
                    }
                    for (var i = 0; i < data.length; i++) {
                        if(fType == 'image'){
                            addFileImageAllItem(index, data[i]);
                        } else {
                            addFileDownLoadAllItem(index, data[i]);
                        }
                    }
                    $this.find('[data-loading-icon]').remove();
                    if(data.length === 1){
                        $this.find('.file-checkbox').hide(0);
                    } else{
                        $this.find('[data-button-group]').show(0);
                    }
                }
            });
        } else {
            $this.find('[data-loading-icon]').remove();
        }
    }

    function initListEventMobile(obj){
        var index = File2JS.maxIndex++;
        var docId = $(obj).attr('data-doc-id');
        $(obj).attr('data-file-download-mobile', index);
        var fType = $(obj).attr('data-form-type');
        var $this = $(obj);
        // 최초 데이터 로드
        if (docId !== '') {
            $.ajax({
                url: "/common/File2List",
                type: "GET",
                cache: false,
                traditional : true,
                data:{
                    docId:docId
                },
                success: function (data) {
                    if(data.length === 0){
                        $this.find('[data-loading-icon]').remove();
                        return;
                    }
                    for (var i = 0; i < data.length; i++) {
                        if(fType == 'image'){
                            addFileImageItem(index, data[i]);
                        } else {
                            addFileDownLoadItem2(index, data[i]);
                        }
                    }
                    $this.find('[data-loading-icon]').remove();
                    if(data.length === 1){
                        $this.find('.file-checkbox').hide(0);
                    } else{
                        $this.find('[data-button-group]').show(0);
                    }
                }
            });
        } else {
            $this.find('[data-loading-icon]').remove();
        }
    }

    $(document).ready(function () {
        $(document).on('click', '[data-file-container] img.file2-thumbnail', function () {
            $(this).next().trigger('click');
        })

        $(document).on('click', '[data-file-add-button]', function () {
            var $container = $(this).closest('[data-file-container]');
            var index = $container.attr('data-file-container');
            var fType =  $container.attr('data-form-type');
            $('[name=ftFileForm_' + index + ']').find('input[type=file]').remove();
            var $file = $("<input style='width:0px; height:0px; border:0px; display:block; visibility:hidden;' type='file' name='file' multiple/>");

            $file.on('change', function (e) {

                var names = [];
                if ($file[0].files) {
                    for (var i = 0; i < $file[0].files.length; i++) {
                        var arr = $file[0].files.item(i).name.split(/[\\|/]/);
                        var name = arr[arr.length - 1];
                        names.push(name);
                    }
                } else {
                    var arr = $(this).val().split(/[\\|/]/);
                    var name = arr[arr.length - 1];
                    names.push(name);
                }

                var alreadyAddedNames = '';
                for (var i = 0; i < names.length; i++) {
                    $('[data-file-container=' + index + ']').find('[data-file-name]').each(function () {
                        if ($(this).attr('data-file-name') === names[i]) {
                            alreadyAddedNames += (names[i] + "\n");
                        }
                    });
                }

                if (alreadyAddedNames !== '') {
                    alert(alreadyAddedNames + '파일이 이미 추가되었습니다.');
                    return false;
                }

                if(fType === 'image'){
                    for (var i = 0; i < names.length; i++) {
                        var isImage = false;
                        var ext = fnFileExt(names[i]).toLowerCase();
                        for (var j = 0; j < imageType.length; j++) {
                            if (ext == imageType[j]) {
                                isImage = true;
                                break;
                            }
                        }
                        if(!isImage){
                            alert('이미지 파일만 업로드 하실수 있습니다.\n(bmp, png, jpg, jpeg, gif)');
                            return false;
                        }
                    }
                }

                for (var i = 0; i < names.length; i++) {
                    if(fType === 'image'){
                        uploadImageFileItem(index, names[i]);
                    } else {
                        uploadFileItem(index, names[i]);
                    }

                }

                $('[name=ftFileForm_' + index + ']').ajaxForm({
                    'url': '/common/File2Upload',
                    'enctype': 'multipart/form-data',
                    'success': function (result) {
                        var slct = $('[data-file-container=' + index + ']').attr("data-input-name");
                        $('[data-file-container=' + index + ']').attr("data-doc-id", result.docId);
                        $('[data-file-container=' + index + ']').parent().find('input[name=\"'+slct+'\"]').val(result.docId);
                        for (var i = 0; i < result.fileUploadInfoList.length; i++) {
                            if (result.fileUploadInfoList[i].errorCode) {
                                alert(result.fileUploadInfoList[i].errorMessage);
                                removeFileItem(index, result.fileUploadInfoList[i].fileName);
                            } else {

                                //이미지 파일 업로드 컴플리트
                                if(fType === 'image'){
                                    completeImageFileItem(index, result.fileUploadInfoList[i]);
                                    //uploadImageFileItem(index, names[i]);
                                } else {
                                    completeFileItem(index, result.fileUploadInfoList[i]);
                                }
                            }
                        }
                    }
                });
                $('[name=ftFileForm_' + index + ']').submit();
            });

            $('[name=ftFileForm_' + index + ']').append($file);
            $file.trigger('click');
        });

        $(document).on('click', '[data-file-delete-button]', function () {
            var $container = $(this).closest('[data-file-container]');
            var index = $container.attr('data-file-container');
            $('[data-file-container=' + index + ']').find("[data-file-list]").find("input[type=checkbox]:checked").each(function () {
                removeFileItem(index, $.trim($(this).closest('[data-file-item]').find('[data-file-name]').attr('data-file-name')));
            });
        });

        $(document).on('click', '[data-file-select-all-button]', function(){
            var $download = $(this).closest('[data-file-download]');
            var index = $download.attr('data-file-download');
            $('[data-file-download=' + index + ']').find("[data-file-list]").find("input[type=checkbox]:not(:checked)").each(function () {
                $(this).prop("checked", true);
            });
        });

        $(document).on('click', '[data-file-select-delYn-all-button]', function(){
            var $download = $(this).closest('[data-file-all-download]');
            var index = $download.attr('data-file-all-download');
            $('[data-file-all-download=' + index + ']').find("[data-file-list]").find("input[type=checkbox]:not(:checked)").each(function () {
                $(this).prop("checked", true);
            });
        });

        $(document).on('click', '[data-file-zip-button]', function () {
            var $download = $(this).closest('[data-file-download]');
            var index = $download.attr('data-file-download');
            var zipList = [];


            $('[data-file-download=' + index + ']').find("[data-file-list]").find("input[type=checkbox]:checked").each(function () {
                var $item = $(this).closest('[data-file-item]');
                var fileId = $item.attr("data-file-item");
                var secCode = $item.attr("data-sec-code");
                var delYn = "";
                zipList.push({
                    fileId : fileId,
                    secCode : secCode,
                    delYn : delYn
                });
            });
            if(zipList.length === 0){
                alert('파일을 선택해주세요');
                return;
            }
            $("#fileDownloadJson").val(JSON.stringify(zipList));
            document.ftFileDownloadForm.submit();
        });

        $(document).on('click', '[data-file-all-zip-button]', function () {
            var $download = $(this).closest('[data-file-all-download]');
            var index = $download.attr('data-file-all-download');
            var zipList = [];


            $('[data-file-all-download=' + index + ']').find("[data-file-list]").find("input[type=checkbox]:checked").each(function () {
                var $item = $(this).closest('[data-file-item]');
                var fileId = $item.attr("data-file-item");
                var secCode = $item.attr("data-sec-code");
                var delYn = "ALL";
                zipList.push({
                    fileId : fileId,
                    secCode : secCode,
                    delYn : delYn
                });
            });
            if(zipList.length === 0){
                alert('파일을 선택해주세요');
                return;
            }
            $("#fileDownloadJson").val(JSON.stringify(zipList));
            document.ftFileDownloadForm.submit();
        });

        //폼 초기화
        $('[data-file-container]').each(function () {
            initFormEvent(this);
        });

        //다운로드 초기화
        $('[data-file-download]').each(function () {
            initListEvent(this);
        });

        //다운로드 초기화(삭제 flag 상관없이 업로드 했던 모든 파일 목록 조회 form)
        $('[data-file-all-download]').each(function () {
            initAllListEvent(this);
        });

        //다운로드 초기화(모바일-공지사항)
        $('[data-file-download-mobile]').each(function () {
            initListEventMobile(this);
        });

        $('body').append("<form name='ftFileDownloadForm' action='/common/File2ZipDownload' method='post' style='width:0px; height:0px; border:0px; display:block; visibility:hidden;'>" +
            "<input type='hidden' name='fileDownloadJson' id='fileDownloadJson' value=''/>" +
            "</form>");
    });

    window.ftFile2Loaded = true;
})();

