from conftest import *

'''TODO'''
# rotation remodelling (decouple centroids movement as a individual function)
# intensity saturation problem (loosing some spatial information? maybe need to fix on the canvas level? depends on the nature and number of distributions?)
# std going too big or too zero after a while
# mimic simplified quadrapole transform in the canvas (develop some possible transformations on canvas level)
# other distributions implementation (Maxwell-Boltzmann, etc)

dim = (256, 256)
canvas = simulation.DynamicPatterns(*dim)
canvas._distributions = [simulation.GaussianDistribution(canvas, rotation_radians=0.003) for _ in range(15)] # rotation_radians=0.003

for _ in range(5000):
    canvas.update()
    canvas.plot_canvas()




