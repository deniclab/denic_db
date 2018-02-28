from app import app, db
from app.models import User, Oligos, TempOligo


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Oligos': Oligos, 'TempOligo': TempOligo}
