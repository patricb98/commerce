from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import User, Category, Listing, Bid, Comment
from .forms import ListingForm, BidForm, CommentForm


def index(request):
    listings = Listing.objects.filter(active=True)
    return render(request, "auctions/index.html", {"listings": listings})


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

# Create new listing
@login_required
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.creator = request.user
            listing.save()
            messages.success(request, "Listing created successfully!")
            return HttpResponseRedirect(reverse("index"))
    
    else:
        form = ListingForm()
    return render(request, "auctions/create_listing.html", {"form": form})

# Show all categories
def categories(request):
    categories = Category.objects.all()
    return render(request, "auctions/categories.html", {"categories": categories})

# Show all listings in a specific category
def category_listings(request, category_name):
    category = get_object_or_404(Category, name=category_name)
    listings = Listing.objects.filter(category=category, active=True)
    return render(request, "auctions/category_listings.html", {
        "listings": listings,
        "category": category
        })

# Show a listing, add bid, comment and close by owner
def listing_page(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    is_watchlist = request.user in listing.watchlist.all()
    bids = listing.bids.order_by("-amount")
    comments = listing.comments.all()
    bid_form = BidForm()
    comment_form = CommentForm()

    if request.method == "POST":
        # Bidding
        if "place_bid" in request.POST:
            bid_form = BidForm(request.POST)
            if bid_form.is_valid():
                bid_amount = bid_form.cleaned_data["amount"]
                if bid_amount > listing.starting_bid and (not bids or bid_amount > bids.first().amount):
                    bid = bid_form.save(commit=False)
                    bid.listing = listing
                    bid.bidder = request.user
                    bid.save()
                    messages.success(request, "Your bid was placed successfully!")
                    return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))
                else:
                    messages.error(request, "Bid must be greater than the current price")
        
        # Commenting
        elif "add_comment" in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.listing = listing
                comment.commenter = request.user
                comment.save()
                messages.success(request, "Your comment was added successfully")
                return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))
        
        # Closing
        elif "close_auction" in request.POST:
            if request.user == listing.creator: 
                listing.active = False
                listing.save()
                messages.success(request, "Auction Closed!")
                return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))
        
    return render(request, "auctions/listing_page.html", {
        "listing": listing,
        "is_watchlist": is_watchlist,
        "bids": bids,
        "comments": comments,
        "bid_form": bid_form,
        "comment_form": comment_form
        })

# Display users watchlist
@login_required
def watchlist(request):
    listings = request.user.watchlist.all()
    return render(request, "auctions/watchlist.html", {"listings": listings})

# Add or remove from a users watchlist
@login_required
def add_to_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    
    if request.user in listing.watchlist.all():
        listing.watchlist.remove(request.user)
    else:
        listing.watchlist.add(request.user)
    return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))
    