from schemaish.type import File as SchemaishFile

class File(SchemaishFile)

    def __init__(self, file, filename, mimetype, id):
        self.file = file
        self.filename = filename
        self.mimetype = mimetype
        self.id = id

    def __repr__(self):
        return '<couchish.type.File file="%r" filename="%s", mimetype="%s", id="%s">'%(self.file, self.filename, self.mimetype, self.id)

