import os, numpy, PIL
from PIL import Image


def average(path):

    # https://stackoverflow.com/questions/17291455/how-to-get-an-average-picture-from-100-pictures-using-pil
    # Access all PNG files in directory
    allfiles = os.listdir(path)
    imlist = [os.path.join(path, filename) for filename in allfiles if filename[-4:] in [".jpg", ".PNG"]]

    # Assuming all images are the same size, get dimensions of first image
    w, h = Image.open(imlist[0]).size
    N = len(imlist)

    # Create a numpy array of floats to store the average (assume RGB images)
    arr = numpy.zeros((h, w, 3), numpy.float)

    # Build up average pixel intensities, casting each image as an array of floats
    for im in imlist:
        print(im)
        try:
            imarr = numpy.array(Image.open(im), dtype=numpy.float)
            arr = arr + imarr / N
        except TypeError:
            print('ERR:', im)
            pass

    # Round values in array and cast as 8-bit integer
    arr = numpy.array(numpy.round(arr), dtype=numpy.uint8)

    # Generate, save and preview final image
    out = Image.fromarray(arr, mode="RGB")
    out.save(os.path.join(path, "average.jpg"))
