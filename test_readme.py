def test_readme():
    try:
        a = open('docs/_build/html/index.html').read()
        b = open('docs/_build/html/readme_test.html').read()
    
        def cut_and_normalize(foo):
            return foo[foo.find('<body'):foo.find('<footer>')].replace('class="code python highlight-python"', 'class="n"').replace('class="highlight-python"', 'class="n"').replace('href="index.html"', 'href="#"').replace('href="_sources/readme_test.txt"', 'href="_sources/index.txt"').replace('<a class="reference external image-reference" href="http://codecov.io/github/TriOptima/tri.table?branch=master"><img alt="http://codecov.io/github/TriOptima/tri.table/coverage.svg?branch=master" src="http://codecov.io/github/TriOptima/tri.table/coverage.svg?branch=master" /></a>\n', '')

        assert cut_and_normalize(a) == cut_and_normalize(b)
    except IOError:
        pass