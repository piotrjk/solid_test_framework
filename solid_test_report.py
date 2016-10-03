import json
import codecs

from xml.etree.ElementTree import ElementTree, Element, tostring


def append_to_a_json_report(file_path, report_dict, encoding='utf-8'):
    with codecs.open(file_path, 'ab+', encoding=encoding) as jf:
        jf.write(json.dumps(report_dict, skipkeys=False, ensure_ascii=False, check_circular=True, encoding=encoding,
                            sort_keys=False) + '\n')


def create_junit_report_from_json_report(json_report_path, output_xml_path, encoding='utf-8'):

    """
    <?xml version="1.0" encoding="UTF-8"?>
<testsuites>
   <testsuite name="JUnitXmlReporter" errors="0" tests="0" failures="0" time="0" timestamp="2013-05-24T10:23:58" />
   <testsuite name="JUnitXmlReporter.constructor" errors="0" skipped="1" tests="3" failures="1" time="0.006" timestamp="2013-05-24T10:23:58">
      <properties>
         <property name="java.vendor" value="Sun Microsystems Inc." />
         <property name="compiler.debug" value="on" />
         <property name="project.jdk.classpath" value="jdk.classpath.1.6" />
      </properties>
      <testcase classname="JUnitXmlReporter.constructor" name="should default path to an empty string" time="0.006">
         <failure message="test failure">Assertion failed</failure>
      </testcase>
      <testcase classname="JUnitXmlReporter.constructor" name="should default consolidate to true" time="0">
         <skipped />
      </testcase>
      <testcase classname="JUnitXmlReporter.constructor" name="should default useDotNotation to true" time="0" />
   </testsuite>
</testsuites>



    'name': test.get_name() or test.id(),
    'class_name': test.get_class() or test.id(),
    'suite': test.get_module() or test.id(),
    'outcome': self.last_test_case_outcome,
    'time': self.test_case_time,
    'stdout': self.stdout_output,
    'stderr': self.stderr_output,
    'logger': self.logger_output,
    'exc': result.errors
    """

    pass


    root_tag = Element('testsuites')
    root_tag.tail = '\n'
    test_suites = {}

    for line in codecs.open(json_report_path, encoding=encoding):
        tc = json.loads(line, encoding=encoding)

        if tc['suite'] not in test_suites:
            test_suites.update({tc['suite']: Element('testsuite', attrib={'name': tc['suite'], 'tests': 0, 'errors': 0,
                                                                          'failures': 0, 'skipped': 0})})

        test_suites[tc['suite']].attrib['tests'] = int(test_suites[tc['suite']].attrib['tests']) + 1
        if tc['outcome'] == 'fail':
            test_suites[tc['suite']].attrib['failures'] = int(test_suites[tc['suite']].attrib['failures']) + 1
        elif tc['outcome'] == 'error':
            test_suites[tc['suite']].attrib['errors'] = int(test_suites[tc['suite']].attrib['errors']) + 1
        elif tc['outcome'] == 'skip':
            test_suites[tc['suite']].attrib['skipped'] = int(test_suites[tc['suite']].attrib['skipped']) + 1
        else:
            test_suites[tc['suite']].attrib['failures'] = int(test_suites[tc['suite']].attrib['failures']) + 1

        for k in test_suites[tc['suite']].attrib:
            if isinstance(test_suites[tc['suite']].attrib[k], (int, float)):
                test_suites[tc['suite']].attrib[k] = str(test_suites[tc['suite']].attrib[k])

        test_case_element = Element('testcase', attrib={'name': tc['name'], 'classname': tc['class_name'], 'time': tc['time']})
        test_case_element.tail = '\n'

        for k in test_case_element.attrib:
            if isinstance(test_case_element.attrib[k], (int, float)):
                test_case_element.attrib[k] = str(test_case_element.attrib[k])

        if tc['outcome'] == 'pass':
            pass
        elif tc['outcome'] == 'fail':
            failed = Element('failure')
            failed.text = '\n'.join(tc['exc'])
            test_case_element.append(failed)
        elif tc['outcome'] == 'error':
            error = Element('error')
            error.text = '\n'.join(tc['exc'])
            test_case_element.append(error)
        elif tc['outcome'] == 'skip':
            test_case_element.append(Element('skipped'))
            skip = Element('skipped')
            skip.text = '\n'.join(tc['exc'])
        else:
            failed = Element('failure')
            failed.text = '\n'.join(tc['exc'])
            test_case_element.append(failed)


        system_out = Element('system-out')
        system_out.text = tc['stdout'] # tc['logger']
        test_case_element.append(system_out)

        system_err = Element('system-err')
        system_err.text = tc['stderr']
        test_case_element.append(system_err)

        test_suites[tc['suite']].append(test_case_element)

    for s in test_suites:
        root_tag.append(test_suites[s])
    test_suites = None

    #import pdb; pdb.set_trace()

    ElementTree(root_tag).write(output_xml_path, encoding=encoding, xml_declaration=True)
