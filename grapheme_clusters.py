import grapheme

class Gstr(str):
    def __new__(cls, content):
        return str.__new__(cls, content)
    
    def __len__(self):
        return grapheme.length(self)
    
    def __getitem__(self, key):
        if isinstance(key, int):
            if key <= 0:
                g_list = list(grapheme.graphemes(str(self)))
                return g_list[key]
            else: 
                return self.__class__(grapheme.slice(str(self), key, key + 1))
        elif isinstance(key, slice):
            if (key.start and key.start < 0) or (key.stop and key.stop < 0) or key.step != 1:
                g_list = list(grapheme.graphemes(str(self)))
                return "".join(g_list[key.start:key.stop:key.step])
            else:
                return self.__class__(grapheme.slice(str(self), key.start, key.stop))
        else:
            return super().__getitem__(key)
    
    def __contains__(self, item):
        return grapheme.contains(str(self), item)