########                                     ######## 
# Hi there, curious student.                         #
#                                                    #
# This submission script downloads some tests,       #
#  runs the tests against your code,                 #
#and then sends the results to a server for grading. #
#                                                    #
# Changing this script might cause your              #
# submissions to fail.                               #
#You can use the option '--dry-run' to see the tests #
# that would be run without actually running them.   #
########                                     ########

import os, sys, doctest, traceback, urllib.request, urllib.parse, urllib.error, base64, ast, re, imp, ast, json
import hashlib
import pdb


SUBMIT_VERSION = '4.0'

RECEIPT_DIR = os.path.join('.', 'receipts');

session    = 'matrix-002'
grader_url = 'class.coursera.org/%s/assignment' % session
static_url = 'courseratests.codingthematrix.com'
protocol = 'https'
dry_run = False
verbose = False
show_submission = False
show_feedback = False
login = None
password = None

################ FOR VERIFYING SIGNATURE ON TESTS ################
from collections import namedtuple
from hashlib import sha512
hashfn = sha512

PublicKey = namedtuple('PublicKey', ('N', 'e'))

def hash(lines, salt):
    m = hashfn()
    for line in lines:
        m.update(str(line).encode())
    m.update(str(salt).encode())
    return m.digest()

def unsign(m, key): return pow(m, key.e, key.N)

def b2i(m): return int.from_bytes(m, 'little')

def verify_signature(lines, signature, key):
    salt, sig = signature
    hashed = hash(lines, salt)
    return b2i(hashed) == unsign(sig, key)

def verify_signature_lines(lines, key):
    i = iter(lines)
    firstline = next(i)
    salt_str, sign_str = firstline.split(' ')
    (salt, sig) = int(salt_str), int(sign_str)
    return verify_signature(i, (salt, sig), key)

def check_signature(response):
    key = PublicKey(N=10810480223307555270754793974348137028346231911887128372498894236522333862768535904711981770850660563024357718007478468455827997422651868772756940504390694970913100697704378592429214786267348296187069428987220571233110244818841009602583740157557662581909170939997953247229188236715181458561434858401678704933253698171424919513416718407303681363275403114095516851428969948115240989059101545870985909066841768134526273721190057338992190632073739245354402667060338194897351550243889777461715790352313337931,e=356712077277075117461112781152011833907464773700347296194891295955027010053581043972802545021976353698381277440683503945344229100132712230552438667754457538982795034975143122540063545095552633393479508230675918312833788633196124838699032398201767280061)
    return verify_signature_lines(response, key)

def get_asgn_data(asgn_name):
    try:
        with urllib.request.urlopen('http://%s/%s.tests'%(static_url, asgn_name)) as tf:
            response = tf.read().decode('utf8').split('\n')
    except urllib.error.URLError:
        print("Could not find tests for this assignment.  Check your Internet connection.")
        sys.exit(1)
    except urllib.error.HTTPError:
        print("Tests not available for assignment '%s'"%asgn_name)
        sys.exit(1)

    if check_signature(response):
        return ast.literal_eval('\n'.join(response[1:]))
    else:
        print("Assignment data improperly signed!")
        sys.exit(1)

########### END OF SIGNATURE-VERIFICATION CODE ###############

########### SOME AUXILIARY PROCEDURES FOR DOCTESTING #########
def test_format(obj, precision=2):
    tf = lambda o: test_format(o, precision)
    delimit = lambda o: ', '.join(o)
    otype = type(obj)
    if otype is str:
        return repr(obj)
    elif otype is float or otype is int:
        if otype is int:
            obj = float(obj)
        if -0.000001 < obj < 0.000001:
            obj = 0.0
        fstr = '%%.%df' % precision
        return fstr % obj
    elif otype is set:
        if len(obj) == 0:
            return 'set()'
        return '{%s}' % delimit(sorted(map(tf, obj)))
    elif otype is dict:
        return '{%s}' % delimit(sorted(tf(k)+': '+tf(v) for k,v in obj.items()))
    elif otype is list:
        return '[%s]' % delimit(map(tf, obj))
    elif otype is tuple:
        return '(%s%s)' % (delimit(map(tf, obj)), ',' if len(obj) == 1 else '')
    elif otype.__name__ in ['Vec','Mat']:
        entries = tf({x:obj.f[x] for x in obj.f if tf(obj.f[x]) != tf(0)})
        return '%s(%s, %s)' % (otype.__name__, tf(obj.D), entries)
    else:
        return str(obj)
         
def find_lines(varname):
    return [line for line in open(asgn_name+'.py') if line.startswith(varname)]

def find_line(varname):
    ls = find_lines(varname)
    if len(ls) != 1:
        print("ERROR: stencil file should have exactly one line containing the string '%s'" % varname)
        return None
    return ls[0]


def use_comprehension(varname):
    line = find_line(varname)
    try:
        parse_elements = ast.dump(ast.parse(line))
    except SyntaxError:
        raise SyntaxError("Sorry---for this task, comprehension must be on one line.")
    return "comprehension" in parse_elements

def double_comprehension(varname):
    line = find_line(varname)
    try:
        parse_elements = ast.dump(ast.parse(line))
    except SyntaxError:
        raise SyntaxError("Sorry---for this task, comprehension must be on one line.")
    return parse_elements.count("comprehension") == 2

def line_contains_substr(varname, word):
    line = find_line(varname)
    return word in line

def substitute_in_assignment(varname, new_env):
    assignment = find_line(varname)
    g = globals().copy()
    g.update(new_env)
    return eval(compile(ast.Expression(ast.parse(assignment).body[0].value), '', 'eval'), g)

##### END AUXILIARY PROCEDURES FOR TESTS ################

def output(tests, test_vars):
    dtst = doctest.DocTestParser().get_doctest(tests, test_vars, 0, '<string>', 0)
    runner = ModifiedDocTestRunner()
    runner.run(dtst)
    return runner.results

class ModifiedDocTestRunner(doctest.DocTestRunner):
    def __init__(self, *args, **kwargs):
        self.results = []
        return super(ModifiedDocTestRunner, self).__init__(*args, checker=OutputAccepter(), **kwargs)
    
    def report_success(self, out, test, example, got):
        self.results.append(got)
    
    def report_unexpected_exception(self, out, test, example, exc_info):
        exf = traceback.format_exception_only(exc_info[0], exc_info[1])[-1]
        self.results.append(exf)
        sys.stderr.write("TEST ERROR: "+exf) #added so as not to fail silently

class OutputAccepter(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        return True

def do_challenge(login, passwd, sid):
    login, ch, state, ch_aux = get_challenge(login, sid)
    if not all((login, ch, state)):
        print('\n!! Challenge Failed: %s\n' % login)
        sys.exit(1)
    return challenge_response(login, passwd, ch), state

def get_challenge(email, sid):
    values = {'email_address': email, "assignment_part_sid": sid, "response_encoding": "delim"}
    data = urllib.parse.urlencode(values).encode('utf8')
    req  = urllib.request.Request(challenge_url, data)
    with urllib.request.urlopen(req) as resp:
        text = resp.read().decode('utf8').strip()
        # text resp is email|ch|signature
        splits = text.split('|')
        if len(splits) != 9:
            print("Badly formatted challenge response: %s" % text)
            sys.exit(1)
        return splits[2], splits[4], splits[6], splits[8]

def challenge_response(login, passwd, ch):
    sha1 = hashlib.sha1()
    sha1.update("".join([ch, passwd]).encode('utf8'))
    digest = sha1.hexdigest()
    return digest


def submit(parts_string):   
    print('= Coding the Matrix Homework and Lab Submission')

    print('Importing your stencil file')
    try:
        solution = __import__(asgn_name)
        test_vars = vars(solution).copy()
    except Exception as exc:
        print(exc)
        print("!! It seems that you have an error in your stencil file. Please make sure Python can import your stencil before submitting, as in...")
        print("""
      underwood:matrix klein$ python3
      Python 3.4.1 
      >>> import """+asgn_name+"\n")
        sys.exit(1)

    if not 'coursera' in test_vars:
        print("This is not a Coursera stencil.  Make sure your stencil is obtained from http://grading.codingthematrix.com/coursera/")
        sys.exit(1)

    
    print('Fetching problems')
    source_files, problems = get_asgn_data(asgn_name)

    test_vars['test_format'] = test_vars['tf'] = test_format
    test_vars['find_lines'] = find_lines
    test_vars['find_line'] = find_line
    test_vars['use_comprehension'] = use_comprehension
    test_vars['double_comprehension'] = double_comprehension
    test_vars['line_contains_substr'] = line_contains_substr
    test_vars['substitute_in_assignment'] = substitute_in_assignment
    global login
    if not login:
        login = login_prompt()
    global password
    if not password:
        password = password_prompt()
    if not parts_string: 
        parts_string = parts_prompt(problems)

    parts = parse_parts(parts_string, problems)

    for sid, name, part_tests in parts:
        print('== Submitting "%s"' % name)

        coursera_sid = asgn_name + '#' + sid
        #TODO: check challenge stuff
        ch_resp, state = do_challenge(login, password, coursera_sid)

        if dry_run:
            print(part_tests)
        else:
            if 'DEV' in os.environ: sid += '-dev'

            # to stop Coursera's strip() from doing anything, we surround in parens
            results  = output(part_tests, test_vars)
            prog_out = '(%s)' % ''.join(map(str.rstrip, results))
            src      = source(source_files)

            if verbose:
                res_itr = iter(results)
                for t in part_tests.split('\n'):
                    print(t)
                    if t[:3] == '>>>':
                       print(next(res_itr), end='')

            if show_submission:
                print('Submission:\n%s\n' % prog_out)

            feedback = submit_solution(name, coursera_sid, prog_out, src, state, ch_resp)
            print(feedback)


def login_prompt():
    return input('username: ')

def password_prompt():
    return input('password: ')

def parts_prompt(problems):
    print('This assignment has the following parts:')
    # change to list all the possible parts?
    for i, (name, parts) in enumerate(problems):
        if parts:
            print('  %d) %s' % (i+1, name))
        else:
            print('  %d) [NOT AUTOGRADED] %s' % (i+1, name))

    return input('\nWhich parts do you want to submit? (Ex: 1, 4-7): ')

def parse_range(s, problems):
    try:
        s = s.split('-')
        if len(s) == 1:
            index = int(s[0])
            if(index == 0):
                return list(range(1, len(problems)+1))
            else:
                return [int(s[0])]
        elif len(s) == 2:
            return list(range(int(s[0], 0, ), 1+int(s[1])))
    except:
        pass
    return []  # Invalid value

def parse_parts(string, problems):
    pr = lambda s: parse_range(s, problems)
    parts = map(pr, string.split(','))
    flat_parts = sum(parts, [])
    return sum((problems[i-1][1] for i in flat_parts if 0<i<=len(problems)), [])

def submit_solution(name, sid, output, source_text, st, ch_resp):
    b64ize = lambda s: str(base64.encodebytes(s.encode('utf-8')), 'ascii')
    values = { 'challenge_response'  : ch_resp
             , 'assignment_part_sid' : sid
             , 'email_address'       : login
             , 'submission'          : b64ize(output)
             , 'submission_aux'      : b64ize(source_text)
             , 'state'               : st
             }

    submit_url = '%s://%s/submit' % (protocol, grader_url)
    data     = urllib.parse.urlencode(values).encode('utf-8')
    req      = urllib.request.Request(submit_url, data)
    with urllib.request.urlopen(req) as response:
        return response.readall().decode('utf-8')

def import_module(module):
    mpath, mname = os.path.split(module)
    mname = os.path.splitext(mname)[0]
    return imp.load_module(mname, *imp.find_module(mname, [mpath]))

def source(source_files):
    src = ['# submit version: %s\n' % SUBMIT_VERSION]
    for fn in source_files:
        src.append('# %s' % fn)
        with open(fn) as source_f:
            src.append(source_f.read())
        src.append('')
    return '\n'.join(src)

def strip(s): return s.strip() if isinstance(s, str) else s

def canonicalize_key(key_value_pair):
    return tuple(map(lambda s:s.strip(), (key_value_pair[0].upper(), key_value_pair[1])))

if __name__ == '__main__':
    try:
        f = open("profile.txt")
        profile = dict([canonicalize_key(re.match("\s*([^\s]*)\s*(.*)\s*", line).groups()) for line in f])
    except (IOError, OSError):
        print("No profile.txt found")
        profile = {}
    import argparse
    parser = argparse.ArgumentParser()
    helps = [ 'assignment name'
            , 'numbers or ranges of problems/tasks to submit'
            , 'your username (you can make one up)'
            , 'your password (optional)'
            , 'your geographical location (optional, used for mapping activity)'
            , 'display tests without actually running them'
            , 'specify where to send the results'
            , 'use an encrypted connection to the grading server'
            , 'use an unencrypted connection to the grading server'
            ]
    ihelp = iter(helps)
    parser.add_argument('assign', help=next(ihelp))
    parser.add_argument('tasks', default=profile.get('TASKS',None), nargs='*', help=next(ihelp))
    parser.add_argument('--username', '--login', default=profile.get('USERNAME',None), help=next(ihelp))
    parser.add_argument('--password', default=profile.get('PASSWORD',None), help=next(ihelp))
    parser.add_argument('--location', default=profile.get('LOCATION',None), help=next(ihelp))
    parser.add_argument('--dry-run', default=False, action='store_true', help=next(ihelp))
    parser.add_argument('--report', default=profile.get('REPORT',None), help=next(ihelp))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--https', dest="protocol", const="https", action="store_const", help=next(ihelp))
    group.add_argument('--http', dest="protocol", const="http", action="store_const", help=next(ihelp))

    parser.add_argument('--verbose', default=False, action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--show-submission', default=False, action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--show-feedback', default=False, action='store_true', help=argparse.SUPPRESS)

    args = parser.parse_args()
    asgn_name = os.path.splitext(args.assign)[0]
    report = args.report
    location = args.location
    dry_run = args.dry_run
    if args.protocol: protocol = args.protocol
    challenge_url = '%s://class.coursera.org/%s/assignment/challenge' % (protocol, session)
    print("CHALLENGE URL ", challenge_url)
    verbose = args.verbose
    show_submission = args.show_submission
    show_feedback = args.show_feedback
    login = args.username
    password = args.password
    submit(','.join(args.tasks))
