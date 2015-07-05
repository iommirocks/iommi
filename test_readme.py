def test_readme():
    a = open('docs/_build/html/index.html').read()
    b = open('docs/_build/html/readme_test.html').read()
    
    def cut(foo):
        return foo[foo.find('<body'):foo.find('<footer>')]

    assert cut(a) == cut(b.replace('href="index.html"', 'href="#"').replace('href="_sources/readme_test.txt"', 'href="_sources/index.txt"'))