
# this function will upload the file on to server....


def upload(file_obj, mongo):
    uploads_dir = './static/uploads/'       # files will get stored here
    doc_number = mongo.db.counters.find_one_or_404({})['fileCount']
    doc_number += 1
    doc_number = 'DOC' + str(doc_number)
    file_obj.save(uploads_dir+doc_number)
    mongo.db.counters.update({}, {'$inc': {'fileCount': 1}})
    return "file is uploaded successfully!"
