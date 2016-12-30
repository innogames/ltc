//-------------------------------------------------------------------------------------
// Advanced Scroll Progress Tracker
//-------------------------------------------------------------------------------------
// Created          2016-08-10
// Changed          2016-09-08
// Authors          David Whitworth | David@Whitworth.de
// Contributors     Rene Mansveld | R.Mansveld@Spider-IT.de
//-------------------------------------------------------------------------------------
// Version 1.0
//-------------------------------------------------------------------------------------
// 2016-08-10       Created
// 2016-08-11 DW    added automated Stops for each article within the tracked area;
//                  added article headlines to the stops of vertical Trackers
// 2016-08-12 DW    now builds the html structure from within the script;
//                  added configurable options;
//                  added titles (if set to 'true') to the horizontal tracker;
//                  added the finalStop option to create an additional stop at the very
//                  end of the progress tracker(s);
//                  stops are now created for each .trackThis instead of article
// 2016-08-13 DW    added the (configurable) title of the additional final stop;
//                  added the automatic override of horTitlesOffset and
//                  horOnlyActiveTitle for small screens;
//                  added the option to hide trackers on large screens
// 2016-08-15 DW    changed the way the tracker works in terms of the scroll
//                  position (bottom of viewport instead of top);
//                  added the option to revert this behavior to top of viewport;
//                  forced skipHeadlines on small screens if horTitles is true
// 2016-08-16 DW    added options to automatically generate the trackers;
//                  added positioning options for the trackers;
//                  set the default value for verTracker to false;
//                  added the class "smallDevice" to all relevant elements when the
//                  viewport width is <= mobileThreshold;
//                  enabled the user to rename section titles on the trackers by
//                  defining a data-name attribute for the headlines - if no data-name
//                  is defined, the text of the headline will be used as before
// 2016-08-16 RM    created a routine that checks if h3 tags have class
//                  "trackThis" and automatically generates the necessary
//                  structure around them if true
//-------------------------------------------------------------------------------------
// Version 1.1
//-------------------------------------------------------------------------------------
// 2016-08-17 DW    added an option to track all headlines instead of h3 only and
//                  adjusted RM's routine accordingly;
//                  added the option to place the horizontal tracker inside an existing
//                  header tag on the site;
//                  cleaned up the script (changed the order of the options and
//                  categorized them)
// 2016-08-19 DW    adds the according class if a horStyle/verStyle is set;
//                  fixed the values for linking, horOnlyActiveTitles / skipHeadlines
//                  fixed the title for horOnlyActiveTitle not showing up when horStops
//                  is set to false - it is now bound to horTitles as it should be;
//                  increased the default value for mobileThreshold, so that the
//                  vertical tracker always fits next to the content
// 2016-08-20 DW    moves the vertical tracker 50px closer to the content as soon as
//                  there is enough space;
//                  edited comments to further clean up the script;
//                  revised all the calculations to eliminate redundancy and bugs
// 2016-08-22 DW    changed the names of all classes and ids to prevent possible
//                  conflicts with other plugins
//-------------------------------------------------------------------------------------
// Version 1.2
//-------------------------------------------------------------------------------------
// 2016-08-23 DW    adjusted the trackAllHeadlines option to only track the headlines
//                  within the tracked area (i.e. either #TrackScrollProgress or body);
//                  changed the way tracker titles are generated to "only first";
//                  adjusted the positioning of the vertical tracker in relataion to
//                  the mobileThreshold and the viewport width;
//                  added the trackViewportOnly option and it's programming;
//                  added the options horColor/verColor;
// 2016-09-02 DW    removed the horizontal tracker's container where it's not needed;
//                  moved the different color schemes to extra files;
//                  changed the way horTitlesOffset works - margin-top of the titles
//                  is now dynamically calculated to maximize customizability;
//                  fixed the calculation for the head-variable so that it takes into
//                  account possible changes the user makes to the height/position of
//                  the horizontal tracker;
//                  created a failsafe for the width of ".spt-centerAll" so that the
//                  vertical tracker doesn't accidentally intersect the content
// 2016-09-08 DW    fixed the calculations of the head variable and redid the whole
//                  linking functionality
//-------------------------------------------------------------------------------------
// Copyright (c) 2016
//-------------------------------------------------------------------------------------

$.fn.progressTracker = function(options) {
    // Default Options -->
    var settings = $.extend({
        // HORIZONTAL tracker -->
        horTracker: true,               // displays a HORIZONTAL scroll progress tracker
        horInHeader: false,             // creates the HORIZONTAL tracker within an existing <header> if true
                                        // ---> naturally, you need to have a header in your markup for this to work; if this is active, then horPosition will be ignored
        horPosition: 'top',             // creates the HORIZONTAL tracker at the top of the page if set to 'top', at the bottom if set to 'bottom'
        horCenter: true,                // makes the HORIZONTAL tracker span the full width of the viewport if set to false
        horStyle: 'fill',               // Sets the style of the HORIZONTAL tracker
                                        // ---> 'beam', 'fill'
        horColor: 'red',                // Sets the color of the default gradient for the HORIZONTAL tracker
                                        // ---> 'red', 'blue', 'green', 'orange', 'silver'
        horMobile: true,                // displays the HORIZONTAL tracker also on small screen devices if true
        horMobileOnly: false,           // hides the HORIZONTAL tracker on large screens if true
                                        // ---> useful if you want to use the VERTICAL tracker for large devices and the HORIZONTAL tracker for small screen; overrides 'horMobile: false'
        horStops: true,                 // adds stops for each section to the HORIZONTAL tracker if true
        horNumbering: true,             // adds numbers to the stops of the HORIZONTAL TRACKER if true
                                        // ---> only used if horStops is true
        horTitles: false,               // adds the headline (h3) of each section to the HORIZONTAL tracker if true
        horTitlesOffset: 'bottom',      // moves the titles of the horizontal tracker off the progress bar if set to 'top' or 'bottom' (they overlay the bar if false)
                                        // ---> only used if horTitles is true; this is automatically set to 'bottom' on small screen devices(!) if set to false
        horOnlyActiveTitle: true,       // displays only the headline of the currently active section in order to deal with space limitations if true
                                        // ---> only used if horTitles is true; this is automatically forced on small screen devices(!)
        // <-- HORIZONTAL tracker
        
        // VERTICAL tracker -->
        verTracker: false,              // displays a VERTICAL scroll progress tracker
        verPosition: 'left',            // creates the VERTICAL tracker on the left side of the page if set to 'left', at the right side if set to 'right'
        verStyle: 'beam',               // Sets the style of the VERTICAL tracker
                                        // ---> 'beam', 'fill'
        verColor: 'red',                // Sets the color of the default gradient for the VERTICAL tracker
                                        // ---> 'red', 'blue', 'green', 'orange', 'silver'
        verMobile: false,               // displays the VERTICAL tracker also on small screen devices if true
        verMobileOnly: false,           // hides the VERTICAL tracker on large screens if true;
                                        // ---> the counterpart for horMobileOnly; only here for completeness, I don't see a reason to actually use this ;)
        verStops: true,                 // adds stops for each section to the VERTICAL tracker if true
        verNumbering: false,            // adds numbers to the stops of the VERTICAL TRACKER if true
                                        // ---> only used if verStops is true
        verTitles: true,                // adds the headline (h3) of each section to the VERTICAL tracker if true
        // <-- VERTICAL tracker
        
        // General -->
        mobileThreshold: 1300,          // sets the viewport width below which a device is considered 'small screen' for the rest of the options
        trackAllHeadlines: false,       // if set to true, all headlines (h1, h2, h3 etc.) within .spt-trackThis will be converted to tracker titles (if horTitles/verTitles is also true), if set to false only h3-headlines will be tracked
        addFinalStop: false,            // adds a final stop to the very end of the progress tracker(s) if true
                                        // ---> only used if horStops and/or verStops is true; works with horNumbering/verNumbering
        finalStopTitle: '',             // adds a title to the final stop at the end of the progress tracker(s) if not ''
                                        // ---> only used if addFinalStop and horTitles/verTitles are true; works without addFinalStop only on the HORIZONTAL tracker and only if horOnlyActiveTitle is true
        hovering: true,                 // adds a hover effect to the stops if true
                                        // ---> only used if horStops/verStops and/or horTitles/verTitles is true
        linking: true,                  // clicking on a stop animates the page to that section if true
                                        // ---> only used if horStops/verStops and/or horTitles/verTitles is true
        skipHeadlines: false,           // clicking on a stop will scroll to right after the headline if true
                                        // ---> only used if horStops/verStops and/or horTitles/verTitles and linking is true; this setting is automatically applied on small screen devices if horTitles is set to true
        scrollSpeed: 800,               // sets the duration of the scrolling animation in milliseconds; set to 0 to scroll w/o animation
                                        // ---> only used if horStops/verStops and/or horTitles/verTitles and linking is true
        trackViewport: true,            // if true the tracker(s) show the scroll position based on the BOTTOM of the viewport, if false the TOP of the viewport serves as the basis
                                        // ---> if the tracked area or even it's last section isn't as high (or higher) as the viewport, then the tracker(s) won't reach 100% if this is set to false
        trackViewportOnly: false        // turns section stops and titles inactive again, when the corresponding section leaves the viewport
        // <-- General
    }, options);
    // <-- Default options
    
    var linkingScrollTop,
        head,
        trackedArea,
        horizontalTracker,
        getScrollProgressMax,
        getScrollProgressValue,
        trackerSize,
        headlineMargin,
        horizontalCenter, horizontalTop, horizontalBottom,
        horizontalTitlesHeight;
    
    // Calculate 'max' and current 'value' for the progress-tag -->
    getScrollProgressMax = function() {
        return trackedArea.outerHeight();
    };
    if (settings.trackViewport || settings.trackViewportOnly) {
        trackerSize = $(window).scrollTop() + $(window).height();
        getScrollProgressValue = function() {
            return $(window).scrollTop() + $(window).height() - trackedArea.offset().top;
        };
    } else {
        trackerSize = $(window).scrollTop();
        getScrollProgressValue = function() {
            return $(window).scrollTop() - trackedArea.offset().top + head;
        };
    }
    // <-- Calculate 'max' and current 'value' for the progress-tag
    
    $(document).ready(function () {
        horizontalCenter = $('.spt-horizontalScrollProgress').outerHeight(true) - $('.spt-horizontalScrollProgress').height() + $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
        horizontalTop = horizontalCenter - $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
        horizontalBottom = horizontalCenter + $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
        horizontalTitlesHeight = parseFloat($('.spt-scrollStopTitles').css('line-height'));

        if (parseFloat($('.spt-centerAll').css('max-width')) > (settings.mobileThreshold - 400)) {
            $('.spt-centerAll').css('max-width', settings.mobileThreshold - 400 + 'px');
        }
        
        // Convert document if headline has class 'spt-trackThis' -->
        if ($('.spt-sectionTitle.spt-trackThis').length) {
            var i = 0;
            $('.spt-sectionTitle.spt-trackThis').each(function() {
                i ++;
                $(this).removeClass('spt-trackThis').wrap('<div id="Section' + i + '" class="spt-trackThis"></div>');
                var nextBreak = false;
                while (!nextBreak) {
                    if ($('#Section' + i).next().length) {
                        if ($('#Section' + i).next()[0] != $('#Section' + i).siblings('.spt-sectionTitle.spt-trackThis')[0]) {
                            $('#Section' + i).append($('#Section' + i).next());
                        }
                        else {
                            nextBreak = true;
                        }
                    }
                    else {
                        nextBreak = true;
                    }
                }
            });
        }
        // <-- Convert document if headline has class 'spt-trackThis'

        if ($('#TrackScrollProgress').length) {
            trackedArea = $('#TrackScrollProgress');
        } else {
            trackedArea = $(document);
        }
        if (settings.trackAllHeadlines) {
            trackedArea.find('h1, h2, h3, h4, h5, h6').addClass('spt-sectionTitle');
        } else {
            trackedArea.find('h3').addClass('spt-sectionTitle');
        }
        
        headlineMargin = (trackedArea.find('.spt-trackThis').children('.spt-sectionTitle:first').outerHeight(true) - trackedArea.find('.spt-trackThis').children('.spt-sectionTitle:first').outerHeight()) / 2;
        trackedArea.find('.spt-trackThis:first').children('.spt-sectionTitle').css('margin-top', '0');
        // Generate tracker html structure -->
        if (settings.horTracker) {
            // Generate HORIZONTAL tracker IN HEADER -->
            if (settings.horInHeader && $('header').length) {
                if (settings.horInHeader == 'bottom') {
                    $('header').append('<div class="spt-horizontalScrollProgress"></div>');
                } else {
                    $('header').prepend('<div class="spt-horizontalScrollProgress"></div>');
                }
                if (settings.horMobileOnly) {
                    $('.spt-horizontalScrollProgress').addClass('spt-mobileOnly');
                }
                head = $('header').outerHeight();
            } else {
                $('body').append('<div class="spt-horizontalScrollProgress spt-fixed"></div>');
                if (settings.horPosition == 'bottom') {
                    head = 0;
                } else {
                    head = $('.spt-horizontalScrollProgress').outerHeight();
                }
            }
            // <-- Generate HORIZONTAL tracker IN HEADER
            
            if (!settings.trackViewportOnly && 'max' in document.createElement('progress')) {
                // Generate html5 progress-tag if it is supported by the browser -->
                $('.spt-horizontalScrollProgress').append('<progress class="spt-scrollProgress"></progress>');
                horizontalTracker = $('.spt-scrollProgress');
            } else {
                // Generate fallback solution for older browsers where the progress-tag is NOT supported -->
                $('.spt-horizontalScrollProgress').append('<div class="spt-scrollProgressContainer"><span class="spt-scrollProgressBar"></span></div>');
                horizontalTracker = $('.spt-scrollProgressContainer');
            }
            if (settings.horPosition == 'bottom' && !settings.horInHeader) {
                $('.spt-horizontalScrollProgress').addClass('spt-bottom');
                $('body').css('padding-bottom', $('.spt-horizontalScrollProgress').height());
            } else {
                if (!settings.horInHeader) {
                    $('body').css('padding-top', $('.spt-horizontalScrollProgress').height());
                }
            }
        }

        // include color-stylesheets if needed -->
        if (settings.horColor == 'blue' || settings.verColor == 'blue') {
            $('head').append('<link href="css/themes/spt-blue.min.css" rel="stylesheet" />');
        } else if (settings.horColor == 'green' || settings.verColor == 'green') {
            $('head').append('<link href="css/themes/spt-green.min.css" rel="stylesheet" />');
        } else if (settings.horColor == 'orange' || settings.verColor == 'orange') {
            $('head').append('<link href="css/themes/spt-orange.min.css" rel="stylesheet" />');
        } else if (settings.horColor == 'custom' || settings.verColor == 'custom') {
            $('head').append('<link href="css/themes/spt-custom.css" rel="stylesheet" />');
        }
        // <-- include color-stylesheets if needed

        // HORIZONTAL tracker -->
        if (settings.horTracker) {
            if ($('.spt-scrollProgress').length) {
                $('.spt-scrollProgress').attr('value', '0');
            }
            if (settings.horTitles) {
                $('<div class="spt-scrollStopTitles"></div>').insertAfter(horizontalTracker);
                $('.spt-scrollStopTitles').append('<div class="spt-stopTitle spt-onlyActive" style="font-weight: bold;"></div>');
            } else {
                horizontalTracker.addClass('spt-untitled');
            }
            if (settings.horStops) {
                $('<div class="spt-scrollStopContainer"></div>').insertAfter(horizontalTracker);
            }
            if (settings.addFinalStop) {
                $('.spt-scrollStopContainer').append('<div class="spt-finalStopCircle" title="' + settings.finalStopTitle + '"></div>');
                if (!settings.horOnlyActiveTitle) {
                    $('.spt-scrollStopTitles').append('<div class="spt-finalStopTitle">' + settings.finalStopTitle + '</div>');
                }
            }
            if (!settings.horMobile) {
                $('.spt-horizontalScrollProgress').addClass('spt-desktopOnly');
            }
            if (settings.horMobileOnly) {
                $('.spt-horizontalScrollProgress').removeClass('spt-desktopOnly').addClass('spt-mobileOnly');
            }
            if (settings.horStyle == 'fill') {
                $('.spt-horizontalScrollProgress').addClass('spt-styleFill');
            }
            
            if (settings.horColor == 'blue') {
                $('.spt-horizontalScrollProgress').addClass('spt-blue');
            } else if (settings.horColor == 'green') {
                $('.spt-horizontalScrollProgress').addClass('spt-green');
            } else if (settings.horColor == 'orange') {
                $('.spt-horizontalScrollProgress').addClass('spt-orange');
            } else if (settings.horColor == 'custom') {
                $('.spt-horizontalScrollProgress').addClass('spt-custom');
            }
            
            if (settings.horCenter) {
                horizontalTracker.addClass('spt-centerAll');
                $('.spt-scrollStopTitles').addClass('spt-centerAll');
                $('.spt-scrollStopContainer').addClass('spt-centerAll');
                
            }
        }
        // <-- HORIZONTAL tracker

        // VERTICAL tracker -->
        if (settings.verTracker) {
            $('body').append('<div class="spt-verticalScrollProgress"><div class="spt-verticalScrollProgressContainer"><div class="spt-verticalScrollProgressBar"></div></div></div>');
            if (settings.verPosition == 'right') {
                $('.spt-verticalScrollProgress').addClass('spt-verRight');
            }

            var verticalTracker = $('.spt-verticalScrollProgress');
            if (!settings.verMobile) {
                verticalTracker.addClass('spt-desktopOnly');
            }
            if (settings.verMobileOnly) {
                verticalTracker.removeClass('spt-desktopOnly').addClass('spt-mobileOnly');
            }
            if (settings.verStops) {
                verticalTracker.append('<div class="spt-vertScrollStopContainer"></div>');
            }
            if (settings.verTitles) {
                verticalTracker.append('<div class="spt-vertScrollStopTitles"></div>');
            } else {
                verticalTracker.addClass('spt-untitled');
            }
            if (settings.addFinalStop) {
                $('.spt-vertScrollStopContainer').append('<div class="spt-finalStopCircle"></div>');
                $('.spt-vertScrollStopTitles').append('<div class="spt-finalStopTitle">' + settings.finalStopTitle + '</div>');
            }
            if (settings.verStyle == 'fill') {
                $('.spt-verticalScrollProgress').addClass('spt-styleFill');
            }
            
            if (settings.verColor == 'blue') {
                $('.spt-verticalScrollProgress').addClass('spt-blue');
            } else if (settings.verColor == 'green') {
                $('.spt-verticalScrollProgress').addClass('spt-green');
            } else if (settings.verColor == 'orange') {
                $('.spt-verticalScrollProgress').addClass('spt-orange');
            } else if (settings.verColor == 'custom') {
                $('.spt-verticalScrollProgress').addClass('spt-custom');
            }
        }
        // <-- VERTICAL tracker

        // <-- generate tracker html structure

        // HORIZONTAL tracker functionality -->
        if ($('.spt-scrollProgress').length) {
            // <progress> tag is supported -->
            var scrollProgress = $('.spt-scrollProgress');
                scrollProgress.attr('max', getScrollProgressMax());
            $(document).scroll(function () {
                if (trackedArea >= trackedArea.offset().top - head) {
                    $(window).resize();
                    scrollProgress.attr('value', getScrollProgressValue());
                } else {
                    scrollProgress.attr('value', '0');
                }
            });
            $(window).resize(function () {
                scrollProgress.attr('max', getScrollProgressMax()).attr('value', getScrollProgressValue());
            });
        } else {
            // <progress> tag is not supported (older browsers) -->
            var scrollProgress = $('.spt-scrollProgressBar'),
                scrollProgressMax = getScrollProgressMax(),
                scrollProgressValue, scrollProgressWidth, scrollProgressLeft,
                getScrollProgressWidth = function() {
                    scrollProgressValue = getScrollProgressValue();
                    if (!settings.trackViewportOnly) {
                        scrollProgressWidth = (scrollProgressValue/scrollProgressMax) * 100;
                    } else {
                        scrollProgressWidth = ((trackerSize)/scrollProgressMax) * 100;
                    }
                    if (scrollProgressWidth > 100) {
                        scrollProgressWidth = 100;
                    }
                    scrollProgressWidth = scrollProgressWidth + '%';
                    return scrollProgressWidth;
                },
                setScrollProgressWidth = function() {
                    scrollProgress.css('width', getScrollProgressWidth());
                },
                getScrollProgressLeft = function() {
                    scrollProgressLeft = (($(window).scrollTop() - head)/scrollProgressMax) * 100;
                    if (scrollProgressLeft > 100) {
                        scrollProgressLeft = 100;
                    }
                    scrollProgressLeft = scrollProgressLeft + '%';
                    return scrollProgressLeft;
                },
                setScrollProgressLeft = function() {
                    scrollProgress.css('left', getScrollProgressLeft());
                };
            
            $(document).scroll(function() {
                if (trackerSize >= trackedArea.offset().top - head) {
                    $(window).resize();
                    scrollProgress.css('width', getScrollProgressWidth());
                } else {
                    scrollProgress.css('width', '0%');
                }
            });
            $(window).resize(function () {
                setScrollProgressWidth();
                if (settings.trackViewportOnly) {
                    setScrollProgressLeft();
                }
            });
        }
        // <-- HORIZONTAL tracker functionality
        
        // VERTICAL tracker functionality -->
        var verticalScrollProgress = $('.spt-verticalScrollProgressBar'),
            scrollProgressMax = getScrollProgressMax(),
            scrollProgressValue, scrollProgressHeight, scrollProgressTop,
            getScrollProgressHeight = function() {
                scrollProgressValue = getScrollProgressValue();
                if (!settings.trackViewportOnly) {
                    scrollProgressHeight = (scrollProgressValue/scrollProgressMax) * 100;
                } else {
                    scrollProgressHeight = (trackerSize/scrollProgressMax) * 100;
                }
                if (scrollProgressHeight > 100) {
                    scrollProgressHeight = 100;
                }
                scrollProgressHeight = scrollProgressHeight + '%';
                return scrollProgressHeight;
            },
            setScrollProgressHeight = function() {
                verticalScrollProgress.css('height', getScrollProgressHeight());
            },
            getScrollProgressTop = function() {
                scrollProgressTop = (($(window).scrollTop() - head)/scrollProgressMax) * 100;
                if (scrollProgressTop > 100) {
                    scrollProgressTop = 100;
                }
                scrollProgressTop = scrollProgressTop + '%';
                return scrollProgressTop;
            },
            setScrollProgressTop = function() {
                verticalScrollProgress.css('top', getScrollProgressTop());
            };

        $(document).scroll(function() {
            if (trackerSize >= trackedArea.offset().top - head) {
                $(window).resize();
            } else {
                verticalScrollProgress.css('height', '0%');
            }
            if ($(window).width() <= settings.mobileThreshold) {
                if (settings.horTitles) {
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').addClass('spt-ellipsis');
                }
                if (!settings.horOnlyActiveTitle) {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'none');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'block');
                }
            } else {
                $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-onlyActive').removeClass('spt-ellipsis');
                if (settings.horOnlyActiveTitle) {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'none');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'block');
                } else {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'block');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'none');
                }
            }
        });
        $(window).resize(function () {
            horizontalCenter = $('.spt-horizontalScrollProgress').outerHeight(true) - $('.spt-horizontalScrollProgress').height() + $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
            horizontalTop = horizontalCenter - $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
            horizontalBottom = horizontalCenter + $('.spt-horizontalScrollProgress').children(':first-child').height() / 2;
            $('.spt-scrollStopTitles').append('<div class="spt-placeholder">&nbsp;</div>');
            horizontalTitlesHeight = parseFloat($('.spt-placeholder').height());
            $('.spt-placeholder').remove();

            scrollProgressMax = getScrollProgressMax();
            setScrollProgressHeight();
            if (settings.trackViewportOnly) {
                setScrollProgressTop();
            }
            moveScrollStops();
            
            // Fake responsive webdesign ("small screens") -->
            if ($(window).width() <= settings.mobileThreshold) {
                // is mobile
                $('.spt-horizontalScrollProgress, .spt-scrollProgress, .spt-scrollProgressContainer, .spt-scrollStopContainer, .spt-scrollStopTitles, .spt-verticalScrollProgress').addClass('spt-smallDevice');
                if (!settings.horOnlyActiveTitle) {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'none');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'block');
                }
                if (!settings.horTitlesOffset) {
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('margin-top', horizontalBottom + 5 + 'px').css('margin-left', '8px');
                }
                if (settings.horTracker && settings.horMobile || settings.horTracker && settings.horMobileOnly) {
                    head = $('.spt-horizontalScrollProgress').outerHeight();
                } else {
                    head = 0;
                }
            } else {
                // is not mobile
                $('.spt-horizontalScrollProgress, .spt-scrollProgress, .spt-scrollProgressContainer, .spt-scrollStopContainer, .spt-scrollStopTitles, .spt-verticalScrollProgress').removeClass('spt-smallDevice');
                if (settings.horOnlyActiveTitle) {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'none');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'block');
                } else {
                    $('.spt-scrollStopTitles').children('.spt-stopTitle, .spt-finalStopTitle').css('display', 'block');
                    $('.spt-scrollStopTitles').children('.spt-onlyActive').css('display', 'none');
                }
                if (settings.horTracker && !settings.horMobileOnly) {
                    head = $('.spt-horizontalScrollProgress').outerHeight();
                } else {
                    head = 0;
                }
            }
            if ($(window).width() >= (settings.mobileThreshold + 100)) {
                $('.spt-verticalScrollProgress').css('width', 180 + ($(window).width() - settings.mobileThreshold) / 2 - 50 + 'px');
                $('.spt-vertScrollStopTitles').css('width', 170 + ($(window).width() - settings.mobileThreshold) / 2 - 50 + 'px');
            } else {
                $('.spt-verticalScrollProgress').css('width', '180px');
                $('.spt-vertScrollStopTitles').css('width', '170px');
            }
            // <-- Fake responsive webdesign ("small screens")
        });
        // <-- VERTICAL tracker

        setScrollStops();
        // Create scrollstops and titles -->
        function setScrollStops() {
            trackedArea.find('.spt-trackThis').each(function(index) {
                var sectionHeadline = $(this).children('.spt-sectionTitle:first'),
                    sectionTitle,
                    sectionId = index + 1,
                    scrollHorStops = $('.spt-scrollStopContainer'),
                    scrollVerStops = $('.spt-vertScrollStopContainer'),
                    scrollStopTitles = $('.spt-scrollStopTitles'),
                    scrollVerStopTitles = $('.spt-vertScrollStopTitles');
                    if (sectionHeadline.attr('data-name')) {
                        sectionTitle = sectionHeadline.attr('data-name');
                    } else {
                        sectionTitle = sectionHeadline.text();
                    }
                
                $(this).attr('id', 'Section' + sectionId);
                $(this).children('.spt-sectionTitle:first').attr({ id: 'SectionHeadline' + sectionId});
                
                scrollHorStops.append('<div class="spt-stopCircle spt-stop' + sectionId + '" data-index="' + sectionId + '" title="' + sectionHeadline.text() + '"></div>');
                scrollVerStops.append('<div class="spt-stopCircle spt-stop' + sectionId + '" data-index="' + sectionId + '"></div>');
                scrollStopTitles.append('<div class="spt-stopTitle spt-stop' + sectionId + '" data-index="' + sectionId + '">' + sectionTitle + '</div>');
                scrollVerStopTitles.append('<div class="spt-stopTitle spt-stop' + sectionId + '" data-index="' + sectionId + '">' + sectionTitle + '</div>');
                
                
                if (settings.horNumbering) {
                    scrollHorStops.children('.spt-stopCircle.spt-stop' + sectionId).append(sectionId);
                    if (settings.addFinalStop) {
                        var numStops = scrollHorStops.children('.spt-stopCircle').length + 1;
                        scrollHorStops.children('.spt-finalStopCircle').text(numStops);
                    }
                }
                if (settings.verNumbering) {
                    scrollVerStops.children('.spt-stopCircle.spt-stop' + sectionId).append(sectionId);
                    if (settings.addFinalStop) {
                        var numStops = scrollVerStops.children('.spt-stopCircle').length + 1;
                        scrollVerStops.children('.spt-finalStopCircle').text(numStops);
                    }
                }
            });
            $('.spt-scrollStopContainer').append($('.spt-scrollStopContainer > .spt-finalStopCircle'));
            $(window).resize();
        }
        // <-- Create scrollstops and titles
        
        // Linking mode functionality -->
        if (settings.linking) {
            $('.spt-stopCircle, .spt-stopTitle').click(function () {
                if ($('#SectionHeadline' + $(this).attr('data-index')).length) {
                    if (settings.skipHeadlines || $(window).width() <= settings.mobileThreshold && settings.horTitles) {
                        linkingScrollTop = $('#SectionHeadline' + $(this).attr('data-index')).offset().top + $('#SectionHeadline' + $(this).attr('data-index')).height() - head + 1;
                    } else {
                        linkingScrollTop = $('#SectionHeadline' + $(this).attr('data-index')).offset().top - parseFloat($('#SectionHeadline' + $(this).attr('data-index')).css('margin-top')) - head + 1;
                    }
                } else {
                    linkingScrollTop = $('#Section' + $(this).attr('data-index')).offset().top - head - 2;
                }

                $('html, body').animate( {
                    scrollTop: linkingScrollTop
                }, settings.scrollSpeed);
            });
            $('.spt-finalStopCircle, .spt-finalStopTitle').click(function () {
                if (trackedArea.children(':last-child').children(':first-child').is('.spt-sectionTitle')) {
                    if (settings.skipHeadlines || $(window).width() <= settings.mobileThreshold && settings.horTitles) {
                        linkingScrollTop = trackedArea.children(':last-child').children(':first-child').offset().top + trackedArea.children(':last-child').children(':first-child').height() - head + 1;
                    } else {
                        linkingScrollTop = trackedArea.children(':last-child').children(':first-child').offset().top - parseFloat(trackedArea.children(':last-child').children(':first-child').css('margin-top')) - head + 1;
                    }
                } else {
                    linkingScrollTop = trackedArea.children(':last-child').offset().top - head - 2;
                }

                $('html, body').animate( {
                    scrollTop: linkingScrollTop
                }, settings.scrollSpeed);
            });
        }
        // <-- Linking mode functionality
        
        // Hover-effect -->
        if (settings.hovering) {
            var itemIndex;
            $('.spt-scrollStopContainer .spt-stopCircle, .spt-scrollStopTitles .spt-stopTitle').hover(function() {
                itemIndex = $(this).attr('data-index');
                $('.spt-stopCircle, .spt-stopTitle').removeClass('spt-hover');
                $('.spt-scrollStopContainer .spt-stop' + itemIndex + ', .spt-scrollStopTitles .spt-stop' + itemIndex).addClass('spt-hover');
            }, function() {
                $('.spt-stopCircle, .spt-stopTitle').removeClass('spt-hover');
            });
            $('.spt-vertScrollStopContainer .spt-stopCircle, .spt-vertScrollStopTitles .spt-stopTitle').hover(function() {
                itemIndex = $(this).attr('data-index');
                $('.spt-stopCircle, .spt-stopTitle').removeClass('spt-hover');
                $('.spt-vertScrollStopContainer .spt-stop' + itemIndex + ', .spt-vertScrollStopTitles .spt-stop' + itemIndex).addClass('spt-hover');
            }, function() {
                $('.spt-stopCircle, .spt-stopTitle').removeClass('spt-hover');
            });
            $('.spt-scrollStopContainer .spt-finalStopCircle, .spt-scrollStopTitles .spt-finalStopTitle').hover(function() {
                $('.spt-scrollStopContainer .spt-finalStopCircle, .spt-scrollStopTitles .spt-finalStopTitle').addClass('spt-hover');
            }, function() {
                $('.spt-finalStopCircle, .spt-finalStopTitle').removeClass('spt-hover');
            });
            $('.spt-vertScrollStopContainer .spt-finalStopCircle, .spt-vertScrollStopTitles .spt-finalStopTitle').hover(function() {
                $('.spt-vertScrollStopContainer .spt-finalStopCircle, .spt-vertScrollStopTitles .spt-finalStopTitle').addClass('spt-hover');
            }, function() {
                $('.spt-finalStopCircle, .spt-finalStopTitle').removeClass('spt-hover');
            });
        }
        // <-- Hover-effect
        $(document).scroll();
    });
    // Position scroll stops and titles -->
    function moveScrollStops() {
        trackedArea.find('.spt-trackThis').each(function(index) {
            var section = $(this),
                sectionHeadline = section.children('.spt-sectionTitle:first'),
                sectionTitle = sectionHeadline.text(),
                sectionTopSubtract = trackedArea.offset().top,
                sectionRelativeTop = section.offset().top - trackedArea.offset().top,
                sectionId = index + 1,
                sectionStop = (sectionRelativeTop / getScrollProgressMax()) * 100,
                scrollHorStops = $('.spt-scrollStopContainer'),
                scrollVerStops = $('.spt-vertScrollStopContainer'),
                scrollStopTitles = $('.spt-scrollStopTitles'),
                scrollVerStopTitles = $('.spt-vertScrollStopTitles');
            
            if (sectionStop > 100) {
                sectionStop = 100;
            }
            
            scrollHorStops.children('.spt-stop' + sectionId).css('left', sectionStop + '%');
            scrollVerStops.children('.spt-stop' + sectionId).css('top', sectionStop + '%');
            scrollStopTitles.children('.spt-stop' + sectionId).css('left', sectionStop + '%');
            scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').addClass('spt-reached');
            if (settings.horStyle == 'beam') {
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').css('left', '-8px');
            } else {
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').css('left', '0');
            }
            scrollVerStopTitles.children('.spt-stop' + sectionId).css('top', sectionStop + '%');
            
            if ($(window).scrollTop() <= trackedArea.find('.spt-trackThis:first').offset().top + trackedArea.find('.spt-trackThis:first').children('.spt-sectionTitle:first').outerHeight() - head) {
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').text('');
            }
            if ($(window).scrollTop() >= section.offset().top + section.children('.spt-sectionTitle:first').outerHeight() - head) {
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').text(sectionTitle);
                var viewportBottom = $(window).scrollTop() + $(window).height();
                if (settings.finalStopTitle != '') {
                    if ($(window).width() <= settings.mobileThreshold) {
                        if (($(window).scrollTop() + $(window).height()) >= (trackedArea.offset().top + trackedArea.height() + (headlineMargin * 2)) || ($(window).scrollTop() + $(window).height()) >= $(document).outerHeight()) {
                            scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').text(settings.finalStopTitle);
                        }
                    } else {
                        if (($(window).scrollTop() + $(window).height()) >= $(document).outerHeight()) {
                            scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').text(settings.finalStopTitle);
                        }
                    }
                }
            }
            
            if (settings.horOnlyActiveTitle) {
                scrollStopTitles.children('.spt-stop' + sectionId).css('display', 'none');
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').css('display', 'block');
            } else {
                scrollStopTitles.children('.spt-stop' + sectionId).css('display', 'block');
                scrollStopTitles.children('.spt-stopTitle.spt-onlyActive').css('display', 'none');
            }

            if (settings.horTitlesOffset == 'top') {
                scrollStopTitles.children('.spt-stopTitle').css('margin-top', horizontalTop - horizontalTitlesHeight - 5 + 'px').css('margin-left', '8px');
            } else if (settings.horTitlesOffset == 'bottom') {
                scrollStopTitles.children('.spt-stopTitle').css('margin-top', horizontalBottom + 5 + 'px').css('margin-left', '8px');
                scrollStopTitles.children('.spt-finalStopTitle').css('margin-top', horizontalBottom + 5 + 'px');
            } else {
                scrollStopTitles.children('.spt-stopTitle').css('margin-top', horizontalCenter - horizontalTitlesHeight / 2 - 2 + 'px').css('margin-left', '25px');
                scrollStopTitles.children('.spt-finalStopTitle').css('margin-top', horizontalCenter - horizontalTitlesHeight / 2 - 2 + 'px').css('margin-right', '16px');
            }
            if (settings.horStyle == 'fill') {
                scrollStopTitles.children('.spt-onlyActive').css('margin-top', '0');
            }
            
            if (getScrollProgressValue() >= sectionRelativeTop) {
                $('.spt-stop' + sectionId).addClass('spt-reached');
            } else {
                $('.spt-stop' + sectionId).removeClass('spt-reached');
            }
            if (getScrollProgressValue() >= getScrollProgressMax()) {
                $('.spt-finalStopCircle, .spt-finalStopTitle').addClass('spt-reached');
            } else {
                $('.spt-finalStopCircle, .spt-finalStopTitle').removeClass('spt-reached');
            }
            if (settings.trackViewportOnly) {
                if (getScrollProgressValue() - $(window).outerHeight() >= sectionRelativeTop + section.outerHeight()) {
                    $('.spt-stop' + sectionId).removeClass('spt-reached');
                }
            }
        });
    }
    // <-- Position scroll stops and titles
};
