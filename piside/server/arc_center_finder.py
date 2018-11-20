import time
import math
import os
import sys
import cv2
import numpy as np
from scipy import optimize

from functools import partial

debug = True


def calc_r(contour_t, xc, yc):
    """ calculate the distance of each 2D points from the center (xc, yc) """
    return np.sqrt((contour_t[0] - xc) ** 2 + (contour_t[1] - yc) ** 2)


def gen_f2(contour_t):
    """
    Function generator for arc lease squares.
    :param contour_t:
    :return:
    """

    def f2(c):
        """ calculate the algebraic distance between the data points and the mean circle centered at c=(xc, yc) """
        r_i = calc_r(contour_t, *c)
        return r_i - r_i.mean()

    return f2


def circle_least_squares(contour):
    """
    Does least squares to find circle function from a contour.
    :param contour: The contour to get circle function for.
    :return: (radius, center) The radius and center of the circle
    """
    # http://scipy-cookbook.readthedocs.io/items/Least_Squares_Circle.html

    # If concave
    contour_shape = contour.shape
    contour_r = np.reshape(contour, [contour_shape[0], contour_shape[2]]).T
    center, ier = optimize.leastsq(gen_f2(contour_r), (3888, 3888))
    r_i2 = calc_r(contour_r, center[0], center[1])
    r_2 = np.mean(r_i2)
    r_residu2 = np.sum((r_i2 - r_2) ** 2.0)

    # If convex
    contour_shape = contour.shape
    contour_r = np.reshape(contour, [contour_shape[0], contour_shape[2]]).T
    center_b, ier = optimize.leastsq(gen_f2(contour_r), (0, 0))
    r_i2 = calc_r(contour_r, center_b[0], center_b[1])
    r_2_b = np.mean(r_i2)
    r_residu2 = np.sum((r_i2 - r_2) ** 2.0)

    if r_2_b < r_2:
        return r_2_b, center_b
    else:
        return r_2, center



def contours_mousecallback(img, contours, event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDBLCLK:
        cimg = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
        cv2.drawContours(cimg, contours, -1, (0, 255, 0), thickness=1)
        cv2.imshow('choose_contour', cimg)
        cv2.setMouseCallback('choose_contour', partial(mousecallback, img, contours))
    if event == cv2.EVENT_LBUTTONDOWN:
        print('click',x, y)
        for i in range(len(contours)):
            r = cv2.pointPolygonTest(contours[i], (x,y), False)
            if r >= 0:
                print('found',r)
                cimg = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
                cv2.drawContours(cimg, contours, i, (0, 0, 255), thickness=1)
                radius, center = circle_least_squares(contours[i])
                print('Circle center: ', center, radius)
                center = (int(round(center[0])), int(round(center[1])))
                radius = int(round(radius))
                cv2.circle(cimg, center, round(radius), (0, 255, 0), 1)
                # draw the center of the circle
                cv2.circle(cimg, center, 1, (0, 0, 255), 1)
                cv2.imshow('choose_contour', cimg)


def get_contours(img):
    """
    Get contours bright area in image, find one that is probably from our artificial star.
    :param img: Image tha analyize
    :return: [contours, countours_artificial_star_idx] The contours an index of which one is our artificial star
    """
    mean = np.mean(img)
    stddev = np.std(img)

    ret, thresh = cv2.threshold(img, mean + 1.5 * stddev, 255, 0)
    #    contrast = 4
    #    brightness = -300
    #    img2 = cv2.addWeighted(img, contrast, img, 0, brightness)
    cv2.imshow('thresholds', thresh)
    #cv2.waitKey(0)

    t, contours, hierarchy = cv2.findContours(thresh, 1, 2)

    # filter contours based on area.
    maxarea = -1
    contour_idx = -1
    for i in range(len(contours)):
        cnt = contours[i]
        carea = cv2.contourArea(cnt)
        if carea > maxarea:
            maxarea = carea
            contour_idx = i

    if debug:
        cimg = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
        cv2.drawContours(cimg, contours, -1, (0, 255, 0), thickness=1)
        cv2.imshow('choose_contour', cimg)
        cv2.setMouseCallback('choose_contour', partial(contours_mousecallback, img, contours))
        cv2.waitKey(0)

    return contours, contour_idx


def circles(img, cimg):
    # img = cv2.medianBlur(img, 8)
    img = cv2.GaussianBlur(img, (15, 15), 0)
    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 1,
                               param1=100, param2=35, minRadius=25, maxRadius=0)
    circles_round = np.uint16(np.around(circles))
    for i in circles_round[0, :]:
        mask = np.zeros(img.shape, np.uint8)
        cv2.circle(mask, (i[0], i[1]), i[2], 255, -1)
        circle_mean = cv2.mean(img, mask=mask)[0]
        print(circle_mean)
        if True or circle_mean > 100:
            # draw the outer circle
            cv2.circle(cimg, (i[0], i[1]), i[2], (0, 255, 0), 2)
            # draw the center of the circle
            cv2.circle(cimg, (i[0], i[1]), 1, (0, 0, 255), 1)
    print(circles)
    cv2.imshow('detected circles', cimg)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def contrast(img, brightness=-300, contrast=4):
    img2 = cv2.addWeighted(img, contrast, img, 0, brightness)
    cv2.imshow('test2', img2)
    cv2.waitKey(0)
    return img2


def canny(img):
    edges = cv2.Canny(img, 50, 100)
    cv2.imshow('test2', edges)
    cv2.waitKey(0)


def reduceToVisual(data, brightRange):
    """
    Reduce data to 8bit using back, range as what data should be used.
    @param brightRange: [background, range]
    """
    startTime = time.time()
    ratio = 0
    if (brightRange[1] - brightRange[0]) > 0:
        ratio = 255.0 / float(brightRange[1] - brightRange[0])
    tmpData = np.subtract(data, brightRange[0])
    tmpData = np.multiply(tmpData.astype(float), ratio)
    tmpData = np.add(tmpData, 0.5)
    tmpData = np.clip(tmpData, 0, 255)
    print("TIME: reduceToVisual() " + str(time.time() - startTime) + " s")
    return np.cast[np.uint8](tmpData)


def background_range(img):
    center_window_size = 500
    img_shape = img.shape
    img_shape = [img_shape[0] / 2 - center_window_size / 2, img_shape[1] / 2 - center_window_size / 2]
    center = img[int(img_shape[0]):int(img_shape[0] + center_window_size),
             int(img_shape[1]):int(img_shape[1] + center_window_size)]
    mean = np.mean(center)
    std = np.std(center)

    low = mean
    high = mean + 3 * std
    img2 = reduceToVisual(img, [low, high])
    cv2.imshow('br', img2)
    cv2.waitKey(0)
    return img2


def get_center(img, center_size):
    center_window_size = center_size
    img_shape = img.shape
    img_shape = [img_shape[0] / 2 - center_window_size / 2, img_shape[1] / 2 - center_window_size / 2]
    center = img[int(img_shape[0]):int(img_shape[0] + center_window_size),
             int(img_shape[1]):int(img_shape[1] + center_window_size)]
    return center


def get_rect(img, pt1, pt2):
    """

    :param img:
    :param pt1: (x, y)
    :param pt2: (x,y)
    :return:
    """
    portion = img[pt1[1]:pt2[1], pt1[0]:pt2[0]]
    return portion

def bounds_mousecallback(img, event, x, y, flags, param):
    global bounds
    if event == cv2.EVENT_LBUTTONDOWN:
        print(x,y)
        if len(bounds) >= 2:
            bounds = []
        if len(bounds) == 0 or len(bounds) == 1:
            bounds.append((x,y))

        if len(bounds) == 2:
            cimg = img.copy()
            cv2.rectangle(cimg, bounds[0], bounds[1], (0, 0, 255), 1)
            cv2.imshow('select bounds', cimg)
        else:
            cv2.imshow('select bounds', img)




bounds = []
def main():
    global debug, bounds
    filename = sys.argv[1]
    name, ext = os.path.splitext(filename)

    center_size = 900

    img = cv2.imread(filename, 0)
    color_img = cv2.imread(filename, 1)
    cv2.imshow('select bounds', color_img)
    cv2.setMouseCallback('select bounds', partial(bounds_mousecallback, color_img))
    cv2.waitKey(0)

    if len(bounds) != 2:
        raise Exception('Invalid bounds')

    # img = get_center(img, center_size)
    # color_img = get_center(color_img, center_size)

    img = get_rect(img, bounds[0], bounds[1])
    color_img = get_rect(color_img, bounds[0], bounds[1])
    #cv2.imshow('selection', img)
    #cv2.waitKey(0)

    background_img = cv2.GaussianBlur(img, (127, 127), 0)
    cv2.imshow('background', background_img)
    cv2.imshow('img', img)
    img = img.astype(float) - background_img.astype(float)
    img = reduceToVisual(img, [0, np.max(img)])
    cv2.imshow('background remove', img)
    #cv2.waitKey(0)
    # img = cv2.GaussianBlur(img, (15, 15), 0)

    # if debug:
    #    cv2.namedWindow('test', cv2.WINDOW_NORMAL)
    # img = contrast(img)
    # img = background_range(img)
    get_contours(img)
    # canny(img)
    # cv2.imshow('pre1', img)
    # cv2.imshow('pre2', color_img)
    # cv2.waitKey(0)
    circles(img, color_img)
    # contours, contour_idx = get_contours(img)


    pass


if __name__ == '__main__':
    main()
