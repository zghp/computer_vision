QT += widgets

CONFIG += c++17

INCLUDEPATH += C:/Users/bedik/Desktop/opencv/opencv/build/include

CONFIG(debug, debug|release) {
    LIBS += -LC:/Users/bedik/Desktop/opencv/opencv/build/x64/vc16/lib -lopencv_world4110d
} else {
    LIBS += -LC:/Users/bedik/Desktop/opencv/opencv/build/x64/vc16/lib -lopencv_world4110
}

SOURCES += \
    main.cpp \
    mainwindow.cpp

HEADERS += \
    mainwindow.h

FORMS += \
    mainwindow.ui

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target

