from codetrust.tasks.testkit import load_solution, net


def test_size(net):
    assert load_solution().remote_image_size("http://example.test/img.png") == 1234
