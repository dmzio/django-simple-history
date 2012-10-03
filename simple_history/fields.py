from django.db.models import ForeignKey, OneToOneField

class SimpleHistoryForeignKey(ForeignKey):
    """
        Allows a ForeignKey to work when
        'to' is a string
        
        Kwarg 'sh_to_field' should be a field instance
        with the same arguments as the 'to' field.
    """
    def __init__(self, *args, **kwargs):
        sh_to_field = kwargs.pop("sh_to_field",None)
        if sh_to_field is not None:
            self.sh_to_field = sh_to_field
        else:
            raise ValueError("'sh_to_field' is a required kwarg.")
        super(SimpleHistoryForeignKey,self).__init__(*args, **kwargs)

class SimpleHistoryOneToOneField(OneToOneField):
    """
        Allows a OneToOneField to work when
        'to' is a string
        
        Kwarg 'sh_to_field' should be a field instance
        with the same arguments as the 'to' field.
    """
    def __init__(self, *args, **kwargs):
        sh_to_field = kwargs.pop("sh_to_field",None)
        if sh_to_field is not None:
            self.sh_to_field = sh_to_field
        else:
            raise ValueError("'sh_to_field' is a required kwarg.")
        super(OneToOneField,self).__init__(*args, **kwargs)